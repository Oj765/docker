"""
Signal Receiver
───────────────
Validates and ingests federated signals arriving from peer nodes.

Security checks performed in order:
  1. Replay attack prevention (Redis TTL nonce store)
  2. TTL expiry check
  3. Source node registration check
  4. Rate limit per node (via TrustManager)
  5. Ed25519 signature verification
  6. Confidence threshold gate

Accepted signals are:
  a) Written to MongoDB for audit
  b) Pushed to Redis Stream for async aggregation
  c) Answered with heartbeat to sender's node record
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum

import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.signal import FederatedSignal
from ..core.config import FederatedNetworkSettings
from ..core.crypto import SigningService
from ..node_registry.registry import NodeRegistry
from ..trust_manager.manager import TrustManager

logger = logging.getLogger("federated_network.receiver")


class RejectReason(str, Enum):
    REPLAY          = "replay_attack"
    EXPIRED         = "signal_expired"
    UNKNOWN_NODE    = "unknown_node"
    RATE_LIMITED    = "rate_limited"
    BAD_SIGNATURE   = "invalid_signature"
    LOW_CONFIDENCE  = "confidence_below_threshold"
    MALFORMED       = "malformed_signal"


class ReceiverResult:
    __slots__ = ("accepted", "reject_reason", "signal_id")

    def __init__(
        self,
        accepted: bool,
        signal_id: str,
        reject_reason: RejectReason | None = None,
    ) -> None:
        self.accepted      = accepted
        self.signal_id     = signal_id
        self.reject_reason = reject_reason


class SignalReceiver:
    def __init__(
        self,
        db:             AsyncIOMotorDatabase,
        redis:          aioredis.Redis,
        settings:       FederatedNetworkSettings,
        signing_service: SigningService,
        node_registry:  NodeRegistry,
        trust_manager:  TrustManager,
    ) -> None:
        self._db      = db[settings.MONGODB_SIGNAL_COLLECTION]
        self._redis   = redis
        self._settings = settings
        self._signer  = signing_service
        self._registry = node_registry
        self._trust   = trust_manager

    async def receive(self, signal: FederatedSignal) -> ReceiverResult:
        """
        Full validation pipeline for an inbound signal.
        Returns ReceiverResult indicating accept/reject with reason.
        """
        # ── 1. Replay attack prevention ────────────────────────────────────────
        nonce_key = f"fednet:nonce:{signal.signal_id}"
        already_seen = await self._redis.set(
            nonce_key, "1",
            nx=True,                               # only set if not exists
            ex=self._settings.REPLAY_WINDOW_SECONDS,
        )
        if not already_seen:
            logger.warning("Replay detected: signal_id=%s", signal.signal_id)
            return ReceiverResult(False, signal.signal_id, RejectReason.REPLAY)

        # ── 2. TTL expiry ──────────────────────────────────────────────────────
        if signal.is_expired():
            logger.debug("Expired signal rejected: %s", signal.signal_id)
            return ReceiverResult(False, signal.signal_id, RejectReason.EXPIRED)

        # ── 3. Source node must be registered ─────────────────────────────────
        node = await self._registry.get_node(signal.source_node)
        if node is None:
            logger.warning(
                "Signal from unknown node %s rejected", signal.source_node
            )
            return ReceiverResult(False, signal.signal_id, RejectReason.UNKNOWN_NODE)

        # ── 4. Rate limiting ───────────────────────────────────────────────────
        count = await self._trust.get_signal_count_last_minute(signal.source_node, self._redis)
        if count > self._settings.MAX_SIGNALS_PER_NODE_PER_MINUTE:
            logger.warning(
                "Node %s rate-limited (%d signals/min)", signal.source_node, count
            )
            return ReceiverResult(False, signal.signal_id, RejectReason.RATE_LIMITED)

        # ── 5. Signature verification ──────────────────────────────────────────
        if not self._signer.verify_signal(signal, node.public_key_pem):
            logger.error(
                "Signature verification failed for signal %s from %s",
                signal.signal_id, signal.source_node,
            )
            return ReceiverResult(False, signal.signal_id, RejectReason.BAD_SIGNATURE)

        # ── 6. Confidence gate ─────────────────────────────────────────────────
        if signal.confidence < self._settings.MIN_CONFIDENCE_TO_PUBLISH:
            return ReceiverResult(False, signal.signal_id, RejectReason.LOW_CONFIDENCE)

        # ── Accepted: persist + enqueue ────────────────────────────────────────
        await self._persist(signal)
        await self._enqueue_for_aggregation(signal)
        await self._registry.heartbeat(signal.source_node)
        await self._trust.record_signal_received(signal.source_node, count)

        logger.info(
            "Signal accepted: %s from %s type=%s confidence=%.3f",
            signal.signal_id, signal.source_node, signal.signal_type, signal.confidence,
        )
        return ReceiverResult(True, signal.signal_id)

    async def _persist(self, signal: FederatedSignal) -> None:
        doc = json.loads(signal.model_dump_json())
        doc["received_at"] = datetime.now(timezone.utc)
        try:
            await self._db.insert_one(doc)
        except Exception as exc:
            # Non-fatal: log and continue. Missing a persistence write
            # is better than dropping the signal from processing.
            logger.error("Failed to persist signal %s: %s", signal.signal_id, exc)

    async def _enqueue_for_aggregation(self, signal: FederatedSignal) -> None:
        """Push to Redis Stream for the async signal_aggregator to consume."""
        try:
            await self._redis.xadd(
                self._settings.REDIS_SIGNAL_STREAM,
                {"payload": signal.model_dump_json()},
                maxlen=10_000,     # cap stream length to prevent OOM
                approximate=True,
            )
        except Exception as exc:
            logger.error("Failed to enqueue signal %s: %s", signal.signal_id, exc)
