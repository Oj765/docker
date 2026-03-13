"""
Prior Updater
─────────────
Consumes AggregatedThreatPrior events from Kafka and applies them to the
local threat scoring engine.

Integration contract:
  This module calls `threat_scorer.update_prior(claim_hash, boosted_score)`
  on the existing threat scoring engine. The interface is injected so this
  module stays decoupled from the scorer's implementation details.

The threat scoring engine is expected to expose either:
  a) A Python callable:  await threat_scorer.update_prior(claim_hash, score)
  b) A REST endpoint:    POST /internal/threat/prior  { claim_hash, score }

Both adapters are implemented below; configure via FEDNET_SCORER_ADAPTER.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Awaitable, Optional, Protocol

import httpx
from aiokafka import AIOKafkaConsumer

from ..models.signal import AggregatedThreatPrior
from ..core.config import FederatedNetworkSettings

logger = logging.getLogger("federated_network.prior_updater")


# ── Adapter protocol ──────────────────────────────────────────────────────────

class ThreatScorerAdapter(Protocol):
    async def update_prior(self, claim_hash: str, adjusted_confidence: float) -> None:
        ...


class HttpThreatScorerAdapter:
    """
    Adapter for threat scoring engines exposed as an internal HTTP service.
    Uses the existing /internal/threat/prior endpoint defined in the main platform.
    """
    def __init__(self, base_url: str, api_key: str) -> None:
        self._url    = f"{base_url.rstrip('/')}/internal/threat/prior"
        self._client = httpx.AsyncClient(
            headers={
                "X-Internal-API-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=3.0,
        )

    async def update_prior(self, claim_hash: str, adjusted_confidence: float) -> None:
        try:
            resp = await self._client.post(
                self._url,
                json={"claim_hash": claim_hash, "federated_prior": adjusted_confidence},
            )
            if resp.status_code not in (200, 204):
                logger.warning(
                    "Threat scorer returned %d for claim %s",
                    resp.status_code, claim_hash[:12],
                )
        except Exception as exc:
            logger.error("Failed to update threat scorer: %s", exc)

    async def close(self) -> None:
        await self._client.aclose()


class InProcessThreatScorerAdapter:
    """
    Adapter for when the threat scorer is imported directly (monorepo / same process).
    Pass any async callable matching: async def update_prior(claim_hash, score) -> None
    """
    def __init__(self, fn: Callable[[str, float], Awaitable[None]]) -> None:
        self._fn = fn

    async def update_prior(self, claim_hash: str, adjusted_confidence: float) -> None:
        await self._fn(claim_hash, adjusted_confidence)


# ── Prior Updater ──────────────────────────────────────────────────────────────

class PriorUpdater:
    def __init__(
        self,
        settings:       FederatedNetworkSettings,
        scorer_adapter: ThreatScorerAdapter,
    ) -> None:
        self._settings = settings
        self._scorer   = scorer_adapter
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._running  = False

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self._settings.KAFKA_THREAT_PRIOR_TOPIC,
            bootstrap_servers=self._settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=f"{self._settings.NODE_ID}-prior-updater",
            value_deserializer=lambda v: v.decode("utf-8"),
            auto_offset_reset="latest",   # only process new priors
            enable_auto_commit=True,
        )
        await self._consumer.start()
        self._running = True
        logger.info(
            "Prior updater consuming: %s", self._settings.KAFKA_THREAT_PRIOR_TOPIC
        )
        asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        self._running = False
        if self._consumer:
            await self._consumer.stop()

    async def _consume_loop(self) -> None:
        while self._running:
            try:
                async for msg in self._consumer:
                    if not self._running:
                        break
                    try:
                        prior = AggregatedThreatPrior.model_validate_json(msg.value)
                        await self._apply_prior(prior)
                    except Exception as exc:
                        logger.error("Failed to process prior message: %s", exc)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Prior updater loop error: %s", exc, exc_info=True)
                await asyncio.sleep(2)

    async def _apply_prior(self, prior: AggregatedThreatPrior) -> None:
        """
        Applies the federated prior to the threat scoring engine.
        High-consensus signals get a direct confidence injection.
        """
        logger.debug(
            "Applying prior: claim=%s conf=%.3f nodes=%d",
            prior.claim_hash[:12] + "…",
            prior.adjusted_confidence,
            prior.contributing_nodes,
        )
        await self._scorer.update_prior(prior.claim_hash, prior.adjusted_confidence)
