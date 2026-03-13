"""
Signal Publisher
────────────────
Transforms local detection events into privacy-preserving federated signals
and fans them out to all registered active peer nodes.

Emission rules:
  - Confidence must exceed MIN_CONFIDENCE_TO_PUBLISH (default 0.6)
  - Signal is signed with this node's Ed25519 private key
  - Mutation depth is capped to prevent echo storms
  - Failed deliveries are retried with exponential backoff
  - Delivery failures are logged but never crash the local pipeline
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from ..models.signal import FederatedSignal, SignalType, TopicDomain, hash_claim_text, hash_embedding
from ..core.config import FederatedNetworkSettings
from ..core.crypto import SigningService
from ..node_registry.registry import NodeRegistry

logger = logging.getLogger("federated_network.publisher")


class SignalPublisher:
    def __init__(
        self,
        settings:       FederatedNetworkSettings,
        signing_service: SigningService,
        node_registry:  NodeRegistry,
    ) -> None:
        self._settings       = settings
        self._signer         = signing_service
        self._registry       = node_registry
        self._http_client:   Optional[httpx.AsyncClient] = None

    async def _client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=self._settings.HTTP_PUBLISH_TIMEOUT_SECONDS,
                headers={
                    "Content-Type": "application/json",
                    "X-Fednet-Node": self._settings.NODE_ID,
                },
            )
        return self._http_client

    # ── Public API ─────────────────────────────────────────────────────────────

    async def publish_from_local_detection(
        self,
        *,
        claim_text_normalized: str,
        embedding:             list[float],
        signal_type:           SignalType,
        confidence:            float,
        topic_domain:          TopicDomain,
        region_hint:           Optional[str] = None,
        ttl_seconds:           Optional[int] = None,
    ) -> Optional[FederatedSignal]:
        """
        Entry point called by the local claim processing pipeline.
        Constructs, signs, and fans out the signal.

        Returns the emitted signal (for audit/logging), or None if suppressed.
        """
        if confidence < self._settings.MIN_CONFIDENCE_TO_PUBLISH:
            logger.debug(
                "Signal suppressed: confidence %.3f < threshold %.3f",
                confidence, self._settings.MIN_CONFIDENCE_TO_PUBLISH,
            )
            return None

        signal = FederatedSignal(
            claim_hash=hash_claim_text(claim_text_normalized),
            embedding_hash=hash_embedding(embedding),
            signal_type=signal_type,
            confidence=confidence,
            topic_domain=topic_domain,
            source_node=self._settings.NODE_ID,
            trust_weight=1.0,          # self-published; trust applied by receivers
            ttl_seconds=ttl_seconds or self._settings.DEFAULT_SIGNAL_TTL_SECONDS,
            region_hint=region_hint,
            mutation_depth=0,
        )

        try:
            signal.signature = self._signer.sign_signal(signal)
        except RuntimeError as exc:
            logger.error("Signal signing failed: %s — NOT publishing", exc)
            return None

        await self._fan_out(signal)
        return signal

    async def relay_signal(self, signal: FederatedSignal) -> None:
        """
        Relay an inbound signal from a peer to other peers (gossip propagation).
        Guards against echo storms via mutation_depth cap.
        """
        if signal.mutation_depth >= self._settings.MAX_MUTATION_DEPTH:
            logger.debug(
                "Signal %s at max depth %d — not relaying",
                signal.signal_id, signal.mutation_depth,
            )
            return

        relayed = signal.model_copy(
            update={
                "mutation_depth": signal.mutation_depth + 1,
                "source_node": self._settings.NODE_ID,
                "timestamp": datetime.now(timezone.utc),
                "signature": None,     # will re-sign
            }
        )
        try:
            relayed.signature = self._signer.sign_signal(relayed)
        except RuntimeError as exc:
            logger.error("Relay signing failed: %s", exc)
            return

        await self._fan_out(relayed, exclude_node=signal.source_node)

    # ── Fan-out ────────────────────────────────────────────────────────────────

    async def _fan_out(self, signal: FederatedSignal, exclude_node: Optional[str] = None) -> None:
        peers = await self._registry.get_active_peers()
        if not peers:
            logger.debug("No active peers — signal %s not propagated", signal.signal_id)
            return

        payload = signal.model_dump_json()
        tasks = [
            self._deliver_with_retry(signal.signal_id, peer.endpoint_url, payload)
            for peer in peers
            if peer.node_id != exclude_node
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        delivered = sum(1 for r in results if r is True)
        logger.info(
            "Signal %s fanned out: %d/%d peers delivered",
            signal.signal_id, delivered, len(tasks),
        )

    async def _deliver_with_retry(self, signal_id: str, endpoint_url: str, payload: str) -> bool:
        url = f"{endpoint_url.rstrip('/')}/fednet/v1/signals/receive"
        client = await self._client()
        backoff = self._settings.HTTP_BACKOFF_FACTOR

        for attempt in range(1, self._settings.HTTP_MAX_RETRIES + 1):
            try:
                resp = await client.post(url, content=payload)
                if resp.status_code in (200, 201, 202):
                    return True
                logger.warning(
                    "Signal %s → %s returned %d (attempt %d)",
                    signal_id, url, resp.status_code, attempt,
                )
            except httpx.TransportError as exc:
                logger.warning(
                    "Signal %s → %s transport error (attempt %d): %s",
                    signal_id, url, attempt, exc,
                )
            except Exception as exc:
                logger.error(
                    "Unexpected error delivering signal %s → %s: %s",
                    signal_id, url, exc,
                )
                return False

            if attempt < self._settings.HTTP_MAX_RETRIES:
                await asyncio.sleep(backoff * (2 ** (attempt - 1)))

        return False

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
