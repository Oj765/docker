"""
Trust Manager
─────────────
Maintains and updates dynamic trust scores for every peer node.

Trust Model:
  effective_trust = base_trust × accuracy_history × (1 - volume_penalty)

Where:
  base_trust       ← org_type default (WHO=0.95, GOV=0.90, NGO=0.75, …)
  accuracy_history ← rolling ratio of signals later validated as correct
  volume_penalty   ← non-linear penalty for nodes sending >N signals/min

adjusted_confidence (used in prior update) =
    signal.confidence × source_trust.effective_trust × consensus_factor

consensus_factor = 1 + 0.05 × (corroborating_nodes - 1) capped at 1.5
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.signal import FederatedSignal, TrustScore
from ..core.config import FederatedNetworkSettings

logger = logging.getLogger("federated_network.trust_manager")

MAX_VOLUME_PENALTY  = 0.50   # Never penalise more than 50%
VOLUME_PENALTY_RATE = 0.001  # Per signal above threshold


class TrustManager:
    def __init__(self, db: AsyncIOMotorDatabase, settings: FederatedNetworkSettings) -> None:
        self._col      = db[settings.MONGODB_TRUST_COLLECTION]
        self._settings = settings

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_trust(self, node_id: str) -> Optional[TrustScore]:
        doc = await self._col.find_one({"node_id": node_id})
        if not doc:
            return None
        doc.pop("_id", None)
        return TrustScore(**doc)

    async def get_effective_trust(self, node_id: str) -> float:
        trust = await self.get_trust(node_id)
        if trust is None:
            logger.warning("No trust record for %s — using minimum trust", node_id)
            return self._settings.TRUST_UNKNOWN
        return trust.effective_trust

    # ── Scoring ────────────────────────────────────────────────────────────────

    async def compute_adjusted_confidence(
        self,
        signal: FederatedSignal,
        corroborating_nodes: int = 1,
    ) -> float:
        """
        Core formula:
          adjusted = signal.confidence × effective_trust × consensus_factor
        """
        effective_trust = await self.get_effective_trust(signal.source_node)
        consensus_factor = min(1.0 + 0.05 * (corroborating_nodes - 1), 1.5)
        adjusted = signal.confidence * effective_trust * consensus_factor
        return round(min(adjusted, 1.0), 4)

    # ── Updates ────────────────────────────────────────────────────────────────

    async def record_signal_received(self, node_id: str, signal_count_last_minute: int) -> None:
        """
        Called every time we accept a signal from a node.
        Applies volume penalty if node is sending too fast.
        """
        threshold = self._settings.MAX_SIGNALS_PER_NODE_PER_MINUTE
        excess = max(0, signal_count_last_minute - threshold)
        volume_penalty = min(excess * VOLUME_PENALTY_RATE, MAX_VOLUME_PENALTY)

        await self._col.update_one(
            {"node_id": node_id},
            {
                "$inc":  {"total_signals_sent": 1},
                "$set":  {
                    "volume_penalty": volume_penalty,
                    "last_updated": datetime.now(timezone.utc),
                },
            },
            upsert=False,
        )
        await self._recompute_effective_trust(node_id)

    async def record_signal_validated(self, node_id: str, was_correct: bool) -> None:
        """
        Called when a signal's claim is later confirmed or refuted.
        Adjusts accuracy_history using exponential moving average (α=0.1).
        """
        trust = await self.get_trust(node_id)
        if trust is None:
            return

        alpha = 0.1
        new_accuracy = (
            (1 - alpha) * trust.accuracy_history + alpha * (1.0 if was_correct else 0.0)
        )

        await self._col.update_one(
            {"node_id": node_id},
            {
                "$inc": {"validated_correct": 1 if was_correct else 0},
                "$set": {
                    "accuracy_history": round(new_accuracy, 4),
                    "last_updated": datetime.now(timezone.utc),
                },
            },
        )
        await self._recompute_effective_trust(node_id)
        logger.info(
            "Trust update for %s: accuracy=%.3f correct=%s",
            node_id, new_accuracy, was_correct,
        )

    async def _recompute_effective_trust(self, node_id: str) -> None:
        trust = await self.get_trust(node_id)
        if trust is None:
            return
        # Recompute via model validator by reconstructing
        updated = TrustScore(**trust.model_dump())
        await self._col.update_one(
            {"node_id": node_id},
            {"$set": {"effective_trust": updated.effective_trust}},
        )

    # ── Rate limiting support ──────────────────────────────────────────────────

    async def get_signal_count_last_minute(self, node_id: str, redis) -> int:
        """Uses Redis INCR+EXPIRE for a sliding 60-second window per node."""
        key = f"fednet:rate:{node_id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 60)
        return count
