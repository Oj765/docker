import json
import logging
import os
from typing import Any, Dict

from agent.state import AgentState

try:
    from aiokafka import AIOKafkaProducer
except ImportError:
    AIOKafkaProducer = None

try:
    from models.narrative_graph.neo4j_service import neo4j_db
except Exception:
    neo4j_db = None

logger = logging.getLogger(__name__)


async def _append_audit_record(verdict: Dict[str, Any], state: AgentState) -> str:
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    os.makedirs(log_dir, exist_ok=True)

    audit_path = os.path.join(log_dir, "verdict_audit.jsonl")
    audit_record = {
        "claim_id": state.get("claim_id"),
        "should_respond": state.get("should_respond", False),
        "review_required": state.get("review_required", True),
        "response_text": state.get("response_text", ""),
        "verdict": verdict,
    }

    with open(audit_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(audit_record, ensure_ascii=False) + "\n")

    return audit_path


async def _write_narrative_graph(state: AgentState, verdict: Dict[str, Any]) -> Dict[str, Any]:
    """Write the claim to Neo4j and check for campaign patterns."""
    narrative: Dict[str, Any] = {
        "account_id": state.get("source_account_id", "unknown"),
        "platform": state.get("source_platform", "unknown"),
        "claim_id": state.get("claim_id", "unknown"),
        "linked_claims": [],
        "campaign_id": None,
    }

    if neo4j_db and neo4j_db.driver:
        try:
            await neo4j_db.ingest_post(
                account_id=state.get("source_account_id", "unknown"),
                platform=state.get("source_platform", "unknown"),
                claim_id=state.get("claim_id", "unknown"),
                timestamp=state.get("posted_at", ""),
            )

            # Check for campaign patterns (same account posting multiple claims)
            try:
                from models.narrative_graph.campaign_detector import detect_campaigns
                campaign = await detect_campaigns(
                    state.get("source_account_id", "unknown"),
                    state.get("source_platform", "unknown"),
                )
                if campaign:
                    narrative["linked_claims"] = campaign.get("linked_claims", [])
                    narrative["campaign_id"] = campaign.get("campaign_id")
            except Exception as exc:
                logger.debug("Campaign detection skipped: %s", exc)

            logger.info("Narrative graph updated for claim %s", state.get("claim_id"))
        except Exception as exc:
            logger.warning("Neo4j write failed (non-critical): %s", exc)
    else:
        logger.info("Neo4j not connected. Narrative node created locally only.")

    return narrative


async def output_node(state: AgentState) -> Dict[str, Any]:
    verdict = state.get("verdict")
    if not verdict:
        logger.error("No verdict found in state for claim %s", state.get("claim_id"))
        return {}

    logger.info("Final verdict ready: [%s] Conf: %.2f", verdict["label"], verdict["confidence"])

    # Write to narrative graph
    narrative = await _write_narrative_graph(state, verdict)

    # Append to local audit log
    # Update verdict with narrative data before saving
    verdict["narrative"] = narrative
    audit_path = await _append_audit_record(verdict, state)

    if AIOKafkaProducer is not None:
        logger.info(
            "Kafka library available. Verdict ready for 'verdict_ready' topic publishing. Audit: %s",
            audit_path,
        )
    else:
        logger.info("Persisted verdict to local audit log: %s", audit_path)

    return {"narrative": narrative}
