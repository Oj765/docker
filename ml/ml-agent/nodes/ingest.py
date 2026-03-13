import logging
from datetime import datetime, timezone
from typing import Any, Dict

from agent.state import AgentState

logger = logging.getLogger(__name__)


async def ingest_node(state: AgentState) -> Dict[str, Any]:
    logger.info("Ingesting claim: %s", state.get("claim_id"))

    reasoning = list(state.get("reasoning_chain", []))
    reasoning.append(
        f"Ingest: Received claim from {state.get('source_platform', 'unknown')} and initialized pipeline state."
    )

    return {
        "claim_id": state.get("claim_id", "unknown_claim"),
        "original_text": state.get("original_text", ""),
        "source_platform": state.get("source_platform", "unknown"),
        "source_account_id": state.get("source_account_id", "unknown"),
        "source_post_url": state.get("source_post_url", ""),
        "source_followers": int(state.get("source_followers", 0) or 0),
        "media_urls": list(state.get("media_urls", [])),
        "engagement": dict(state.get("engagement", {})),
        "posted_at": state.get("posted_at") or datetime.now(timezone.utc).isoformat(),
        "atomic_claims": [],
        "evidence": [],
        "reasoning_chain": reasoning,
        "mutation_of": state.get("mutation_of"),
        "mutation_depth": int(state.get("mutation_depth", 0) or 0),
        "satire_flag": False,
        "confidence": 0.0,
        "risk_score": 0.0,
        "predicted_6h_reach": int(state.get("predicted_6h_reach", 0) or 0),
        "verdict": None,
        "should_respond": False,
        "review_required": True,
    }
