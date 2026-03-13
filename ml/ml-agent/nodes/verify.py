import asyncio
import logging
from typing import Any, Dict, List

from agent.state import AgentState

# ---------------------------------------------------------------------------
# Import all 5 evidence tools with safe fallbacks
# ---------------------------------------------------------------------------
try:
    from tools.fact_check_api import search_fact_checks
except Exception:
    async def search_fact_checks(query: str, num_results: int = 3) -> list:
        return []

try:
    from tools.duckduckgo_search import search_evidence
except Exception:
    async def search_evidence(query: str, num_results: int = 5) -> list:
        return []

try:
    from tools.who_api import search_health_data
except Exception:
    async def search_health_data(query: str) -> list:
        return []

try:
    from tools.wikipedia_search import search_wikipedia
except Exception:
    async def search_wikipedia(query: str, num_results: int = 2) -> list:
        return []

try:
    from tools.google_news import search_google_news
except Exception:
    async def search_google_news(query: str, num_results: int = 4) -> list:
        return []

logger = logging.getLogger(__name__)


def _normalize_results(result: Any, source_type: str) -> List[Dict[str, Any]]:
    if not isinstance(result, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for item in result:
        if not isinstance(item, dict):
            continue
        normalized.append({**item, "source_type": item.get("source_type", source_type)})
    return normalized


async def verify_node(state: AgentState) -> Dict[str, Any]:
    claims_to_check = list(state.get("atomic_claims", []))
    if not claims_to_check:
        claims_to_check = [state.get("translated_text") or state.get("original_text", "")]

    all_evidence: List[Dict[str, Any]] = list(state.get("evidence", []))
    reasoning = list(state.get("reasoning_chain", []))

    logger.info("Verifying %s atomic claims across 5 sources in parallel...", len(claims_to_check))

    for claim in claims_to_check:
        try:
            # Run ALL 5 evidence sources in parallel
            raw_fcat, raw_ddg, raw_who, raw_wiki, raw_news = await asyncio.gather(
                search_fact_checks(claim, num_results=3),
                search_evidence(claim, num_results=5),
                search_health_data(claim),
                search_wikipedia(claim, num_results=2),
                search_google_news(claim, num_results=4),
                return_exceptions=True,
            )

            fcat_res = _normalize_results(raw_fcat, "fact_check")
            ddg_res = _normalize_results(raw_ddg, "search")
            who_res = _normalize_results(raw_who, "official")
            wiki_res = _normalize_results(raw_wiki, "encyclopedia")
            news_res = _normalize_results(raw_news, "news")

            all_evidence.extend(fcat_res)
            all_evidence.extend(ddg_res)
            all_evidence.extend(who_res)
            all_evidence.extend(wiki_res)
            all_evidence.extend(news_res)

            reasoning.append(
                f"Verify: Queried 5 sources for '{claim[:60]}...' => "
                f"FCAT={len(fcat_res)}, DDG={len(ddg_res)}, Official={len(who_res)}, "
                f"Wikipedia={len(wiki_res)}, News={len(news_res)}"
            )
        except Exception as exc:
            logger.error("Parallel verification failed for claim '%s': %s", claim, exc)
            reasoning.append("Verify: Evidence gathering failed for one claim; proceeding with partial evidence.")

    # Deduplicate by URL
    seen_urls = set()
    unique_evidence: List[Dict[str, Any]] = []
    for evidence_item in all_evidence:
        url = evidence_item.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        unique_evidence.append(evidence_item)

    reasoning.append(f"Verify: Retained {len(unique_evidence)} unique evidence item(s) after deduplication.")

    return {
        "evidence": unique_evidence,
        "reasoning_chain": reasoning,
    }
