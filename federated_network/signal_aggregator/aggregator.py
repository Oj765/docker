"""
Signal Aggregator
─────────────────
Async consumer that reads from the inbound Redis Stream and produces
AggregatedThreatPrior objects — weighted consensus across all nodes.

Aggregation logic:
  - Groups signals by claim_hash
  - Applies trust-weighted confidence averaging
  - Computes consensus_factor based on corroborating node count
  - Emits AggregatedThreatPrior to Kafka for the threat scoring engine
  - Maintains a Redis hash of current priors for sub-millisecond lookup

Runs as a long-lived background task inside the FastAPI lifespan.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer

from ..models.signal import AggregatedThreatPrior, FederatedSignal, TopicDomain
from ..core.config import FederatedNetworkSettings
from ..trust_manager.manager import TrustManager

logger = logging.getLogger("federated_network.aggregator")

# Redis key prefix for live prior cache
PRIOR_CACHE_PREFIX = "fednet:prior:"
PRIOR_CACHE_TTL    = 3600  # 1 hour


class SignalAggregator:
    def __init__(
        self,
        redis:         aioredis.Redis,
        kafka_producer: AIOKafkaProducer,
        trust_manager: TrustManager,
        settings:      FederatedNetworkSettings,
    ) -> None:
        self._redis    = redis
        self._kafka    = kafka_producer
        self._trust    = trust_manager
        self._settings = settings
        self._running  = False

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Begin consuming the inbound signal stream. Call once at startup."""
        self._running = True
        logger.info("Signal aggregator started — consuming %s", self._settings.REDIS_SIGNAL_STREAM)
        await self._ensure_consumer_group()
        asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        self._running = False
        logger.info("Signal aggregator stopping")

    # ── Consumption loop ───────────────────────────────────────────────────────

    async def _ensure_consumer_group(self) -> None:
        try:
            await self._redis.xgroup_create(
                self._settings.REDIS_SIGNAL_STREAM,
                self._settings.REDIS_CONSUMER_GROUP,
                id="$",
                mkstream=True,
            )
        except Exception:
            pass  # Group already exists — normal on restart

    async def _consume_loop(self) -> None:
        consumer_name = f"{self._settings.NODE_ID}-agg"
        while self._running:
            try:
                messages = await self._redis.xreadgroup(
                    groupname=self._settings.REDIS_CONSUMER_GROUP,
                    consumername=consumer_name,
                    streams={self._settings.REDIS_SIGNAL_STREAM: ">"},
                    count=50,
                    block=1000,   # block up to 1 second — keeps latency <2s
                )
                if not messages:
                    continue

                for stream_name, entries in messages:
                    msg_ids = []
                    signals = []
                    for msg_id, fields in entries:
                        try:
                            signal = FederatedSignal.model_validate_json(fields["payload"])
                            signals.append(signal)
                            msg_ids.append(msg_id)
                        except Exception as exc:
                            logger.warning("Unparseable signal in stream: %s", exc)
                            msg_ids.append(msg_id)  # still ACK to avoid re-delivery

                    if signals:
                        await self._aggregate_batch(signals)

                    if msg_ids:
                        await self._redis.xack(
                            self._settings.REDIS_SIGNAL_STREAM,
                            self._settings.REDIS_CONSUMER_GROUP,
                            *msg_ids,
                        )

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Aggregator consume loop error: %s", exc, exc_info=True)
                await asyncio.sleep(2)

    # ── Aggregation logic ──────────────────────────────────────────────────────

    async def _aggregate_batch(self, signals: list[FederatedSignal]) -> None:
        """
        Group by claim_hash and emit one AggregatedThreatPrior per unique claim.
        """
        groups: dict[str, list[FederatedSignal]] = defaultdict(list)
        for sig in signals:
            groups[sig.claim_hash].append(sig)

        for claim_hash, group in groups.items():
            prior = await self._compute_prior(claim_hash, group)
            if prior:
                await self._emit_prior(prior)

    async def _compute_prior(
        self, claim_hash: str, signals: list[FederatedSignal]
    ) -> Optional[AggregatedThreatPrior]:
        if not signals:
            return None

        # Load per-node effective trust asynchronously
        trust_tasks = [
            self._trust.get_effective_trust(sig.source_node) for sig in signals
        ]
        trusts = await asyncio.gather(*trust_tasks)

        # Weighted confidence sum
        total_weight    = sum(trusts)
        if total_weight == 0:
            return None

        weighted_conf   = sum(
            sig.confidence * trust
            for sig, trust in zip(signals, trusts)
        ) / total_weight

        # Consensus factor: more corroborating nodes → higher factor (capped at 1.5)
        unique_nodes    = len({s.source_node for s in signals})
        consensus_factor = min(1.0 + 0.05 * (unique_nodes - 1), 1.5)
        adjusted_conf   = round(min(weighted_conf * consensus_factor, 1.0), 4)

        # Dominant topic by frequency
        topic_counts: dict[str, int] = defaultdict(int)
        for sig in signals:
            topic_counts[sig.topic_domain] += 1
        dominant_topic_str = max(topic_counts, key=topic_counts.__getitem__)
        dominant_topic = TopicDomain(dominant_topic_str)

        earliest = min(s.timestamp for s in signals)

        # Persist to Redis cache for instant lookup by threat scorer
        prior = AggregatedThreatPrior(
            claim_hash=claim_hash,
            adjusted_confidence=adjusted_conf,
            consensus_factor=round(consensus_factor, 3),
            contributing_nodes=unique_nodes,
            dominant_topic=dominant_topic,
            earliest_seen=earliest,
            signal_count=len(signals),
            recommendation=self._build_recommendation(adjusted_conf, unique_nodes),
        )

        cache_key = f"{PRIOR_CACHE_PREFIX}{claim_hash}"
        await self._redis.setex(cache_key, PRIOR_CACHE_TTL, prior.model_dump_json())

        return prior

    def _build_recommendation(self, adjusted_conf: float, node_count: int) -> str:
        if adjusted_conf >= 0.85 and node_count >= 3:
            return "HIGH_THREAT: Immediately elevate local risk score"
        if adjusted_conf >= 0.70:
            return "ELEVATED: Increase prior probability by 0.15"
        if adjusted_conf >= 0.55:
            return "MODERATE: Increase prior probability by 0.08"
        return "LOW: Monitor only"

    # ── Kafka emission ─────────────────────────────────────────────────────────

    async def _emit_prior(self, prior: AggregatedThreatPrior) -> None:
        """
        Publish the aggregated prior to Kafka topic `threat.prior.update`.
        The existing threat scoring engine subscribes to this topic.
        """
        try:
            await self._kafka.send(
                self._settings.KAFKA_THREAT_PRIOR_TOPIC,
                value=prior.model_dump_json(),
                key=prior.claim_hash.encode("utf-8"),
            )
            logger.info(
                "Prior emitted: claim=%s conf=%.3f nodes=%d",
                prior.claim_hash[:12] + "…",
                prior.adjusted_confidence,
                prior.contributing_nodes,
            )
        except Exception as exc:
            logger.error("Failed to emit prior to Kafka: %s", exc)

    # ── Lookup API (used by FastAPI endpoints) ─────────────────────────────────

    async def get_current_prior(self, claim_hash: str) -> Optional[AggregatedThreatPrior]:
        """Fast Redis lookup of current aggregated prior for a claim."""
        raw = await self._redis.get(f"{PRIOR_CACHE_PREFIX}{claim_hash}")
        if raw is None:
            return None
        return AggregatedThreatPrior.model_validate_json(raw)
