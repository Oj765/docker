import asyncio
import logging

logger = logging.getLogger(__name__)

# Try the new 'ddgs' package first, fall back to old 'duckduckgo_search'
DDGS = None
try:
    from ddgs import DDGS as _DDGS
    DDGS = _DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS as _DDGS
        DDGS = _DDGS
    except ImportError:
        logger.warning("Neither 'ddgs' nor 'duckduckgo_search' is installed.")


def _score_url(url: str) -> float:
    if any(domain in url for domain in ["who.int", "cdc.gov", "nih.gov"]):
        return 0.95
    if ".gov" in url or ".edu" in url:
        return 0.85
    if any(domain in url for domain in ["reuters.com", "apnews.com", "bbc.com"]):
        return 0.85
    return 0.6


async def search_evidence(query: str, num_results: int = 5) -> list:
    """Search DuckDuckGo for web evidence. Free, no API key needed."""
    if DDGS is None:
        logger.error("DuckDuckGo search not available. Install: pip install ddgs")
        return []

    logger.info("Querying DuckDuckGo for: %s", query[:80])

    try:
        def _run_search() -> list:
            results = []
            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=num_results):
                    url = item.get("href", "")
                    results.append({
                        "url": url,
                        "title": item.get("title", ""),
                        "credibility_score": _score_url(url),
                        "excerpt": item.get("body", "")[:300],
                        "source_type": "search",
                    })
            return results

        return await asyncio.to_thread(_run_search)
    except Exception as exc:
        logger.error("DuckDuckGo search error: %s", exc)
        return []
