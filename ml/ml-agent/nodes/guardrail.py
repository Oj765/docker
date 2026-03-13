import logging
from typing import Any, Dict

from agent.state import AgentState

logger = logging.getLogger(__name__)


def _extract_domain(url: str) -> str:
    parts = url.split("/")
    return parts[2].lower() if len(parts) > 2 else ""


async def guardrail_node(state: AgentState) -> Dict[str, Any]:
    text = state.get("original_text", "").lower()
    evidence = list(state.get("evidence", []))
    reasoning = list(state.get("reasoning_chain", []))

    satire_flag = False
    satire_domains = ["theonion.com", "babylonbee.com", "clickhole.com", "waterfordwhispersnews.com"]

    if any(domain in text for domain in satire_domains):
        satire_flag = True

    if any(marker in text for marker in ["satire", "parody", "joke", "sarcasm"]):
        satire_flag = True

    for evidence_item in evidence:
        url = evidence_item.get("url", "").lower()
        if any(domain in url for domain in satire_domains):
            satire_flag = True

    independent_domains = {
        _extract_domain(evidence_item.get("url", ""))
        for evidence_item in evidence
        if evidence_item.get("url")
    }
    independent_domains.discard("")

    if satire_flag:
        logger.info("Satire detected for claim %s", state.get("claim_id"))
        reasoning.append("Guardrail: Flagged as likely satire/non-serious content based on source and tone checks.")

    if len(independent_domains) < 2 and state.get("confidence", 0.0) > 0.75:
        reasoning.append("Guardrail: Evidence is not yet triangulated across independent domains; human review remains required.")

    return {
        "satire_flag": satire_flag,
        "reasoning_chain": reasoning,
    }
