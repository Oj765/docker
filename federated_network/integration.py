"""
Platform Integration Adapter
─────────────────────────────
This file shows EXACTLY where and how to call the Federated Network
from the existing MisInfo Shield pipeline.

DO NOT modify existing pipeline code beyond the two injection points below.
This follows the Open/Closed principle — extend, don't modify.

─────────────────────────────────────────────────────────────────────────────
INJECTION POINT 1 — After local claim verdict is produced:
  In your existing claim processing pipeline (e.g. reasoning_brain/agent.py),
  after a verdict is written, call:
      await fednet_adapter.publish_detection(verdict)

INJECTION POINT 2 — Before threat score is finalised:
  In your existing threat scoring engine (e.g. threat_scoring/scorer.py),
  before returning the final risk score, call:
      boosted = await fednet_adapter.get_federated_boost(claim_hash)
      final_score = min(base_score + boosted, 1.0)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from .models.signal import SignalType, TopicDomain, hash_claim_text, hash_embedding

logger = logging.getLogger("federated_network.integration")


# ── Category → TopicDomain mapping ────────────────────────────────────────────
# Maps the existing platform's claim category strings to federated TopicDomain

CATEGORY_MAP: dict[str, TopicDomain] = {
    "medical":   TopicDomain.HEALTH,
    "health":    TopicDomain.HEALTH,
    "political": TopicDomain.POLITICS,
    "election":  TopicDomain.ELECTION,
    "science":   TopicDomain.SCIENCE,
    "financial": TopicDomain.FINANCE,
    "military":  TopicDomain.MILITARY,
    "climate":   TopicDomain.CLIMATE,
}


class FederatedNetworkAdapter:
    """
    Thin adapter that the existing pipeline imports.
    Communicates with the federated network service over HTTP
    (works whether it's co-located or on a separate pod).

    Usage in existing pipeline:
        from services.federated_network.integration import FederatedNetworkAdapter

        # Initialise once at app startup (inject via dependency injection)
        fednet = FederatedNetworkAdapter(base_url="http://fednet:8100", node_id="node-local")

        # After verdict
        await fednet.publish_detection(
            claim_text_normalized = verdict.normalized_text,
            embedding             = verdict.embedding,
            confidence            = verdict.confidence,
            category              = verdict.category,
            verdict_label         = verdict.label,
        )

        # Before final score
        boost = await fednet.get_federated_boost(claim_hash)
    """

    def __init__(
        self,
        base_url: str,
        node_id:  str,
        timeout:  float = 2.0,           # Keep tight — never block the pipeline
        enabled:  bool  = True,          # Feature flag for gradual rollout
    ) -> None:
        self._base    = base_url.rstrip("/")
        self._node_id = node_id
        self._enabled = enabled
        self._client  = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "X-Fednet-Node": node_id,
                "Content-Type": "application/json",
            },
        )

    # ── INJECTION POINT 1 ──────────────────────────────────────────────────────

    async def publish_detection(
        self,
        *,
        claim_text_normalized: str,
        embedding:             list[float],
        confidence:            float,
        category:              str,
        verdict_label:         str,        # "FALSE" | "MISLEADING" | "TRUE" | "UNVERIFIED"
        region_hint:           Optional[str] = None,
    ) -> bool:
        """
        Called by the claim processing pipeline after a verdict is produced.
        Publishes a privacy-preserving signal to the federated mesh.
        Returns True if published, False if skipped or failed.

        This method is FIRE-AND-FORGET safe — failures are logged but
        never propagate back to the pipeline. The local verdict is never
        blocked by federation.
        """
        if not self._enabled:
            return False

        # Only publish for harmful verdicts
        if verdict_label not in ("FALSE", "MISLEADING"):
            return False

        topic = CATEGORY_MAP.get(category.lower(), TopicDomain.OTHER)
        signal_type = (
            SignalType.CLAIM_DETECTED
            if verdict_label == "FALSE"
            else SignalType.NARRATIVE_SHIFT
        )

        payload = {
            "claim_text_normalized": claim_text_normalized,
            "embedding":             embedding,
            "signal_type":           signal_type.value,
            "confidence":            confidence,
            "topic_domain":          topic.value,
            "region_hint":           region_hint,
        }

        try:
            resp = await self._client.post(
                f"{self._base}/fednet/v1/signals/publish_local",
                json=payload,
            )
            if resp.status_code in (200, 201, 202):
                logger.debug("Federated signal published for claim hash %s",
                             hash_claim_text(claim_text_normalized)[:12])
                return True
            else:
                logger.warning("Federated publish returned %d", resp.status_code)
                return False
        except Exception as exc:
            logger.warning("Federated publish failed (non-fatal): %s", exc)
            return False

    # ── INJECTION POINT 2 ──────────────────────────────────────────────────────

    async def get_federated_boost(self, claim_hash: str) -> float:
        """
        Called by the threat scoring engine before finalising a risk score.
        Returns a float 0.0–0.3 representing how much to boost the local score
        based on federated consensus.

        Returns 0.0 on any error — never penalises the pipeline.

        Example usage in scorer.py:
            base_score   = self._compute_local_score(claim)
            fed_boost    = await fednet_adapter.get_federated_boost(claim.claim_hash)
            final_score  = min(base_score + fed_boost, 1.0)
        """
        if not self._enabled:
            return 0.0

        try:
            resp = await self._client.get(
                f"{self._base}/fednet/v1/priors/{claim_hash}"
            )
            if resp.status_code == 200:
                data = resp.json()
                adjusted_conf  = data.get("adjusted_confidence", 0.0)
                contributing   = data.get("contributing_nodes", 1)
                # Boost scales with confidence and peer count, capped at 0.30
                boost = min(adjusted_conf * 0.3 * min(contributing / 3, 1.0), 0.30)
                logger.debug(
                    "Federated boost for %s: %.3f (nodes=%d)",
                    claim_hash[:12], boost, contributing,
                )
                return round(boost, 4)
            elif resp.status_code == 404:
                return 0.0   # No federated signal yet — normal
            else:
                logger.warning("Unexpected prior response: %d", resp.status_code)
                return 0.0
        except Exception as exc:
            logger.warning("Federated boost lookup failed (non-fatal): %s", exc)
            return 0.0

    async def close(self) -> None:
        await self._client.aclose()
