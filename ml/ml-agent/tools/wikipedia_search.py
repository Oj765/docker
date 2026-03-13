import asyncio
import logging

logger = logging.getLogger(__name__)

try:
    import wikipediaapi
    _wiki = wikipediaapi.Wikipedia(
        user_agent="MisinfoShield/1.0 (hackathon project)",
        language="en",
    )
except ImportError:
    _wiki = None
    logger.warning("wikipedia-api not installed. pip install wikipedia-api")


async def search_wikipedia(query: str, num_results: int = 2) -> list:
    """Search Wikipedia for factual information. Completely free, no API key.

    Wikipedia is one of the most reliable secondary sources for verifying
    well-known factual claims (health, science, politics, geography).
    """
    if _wiki is None:
        return []

    logger.info("Querying Wikipedia for: %s", query[:80])

    try:
        def _run_search() -> list:
            results = []

            # Search for the most relevant page
            page = _wiki.page(query)
            if page.exists():
                results.append({
                    "url": page.fullurl,
                    "title": f"Wikipedia: {page.title}",
                    "credibility_score": 0.75,
                    "excerpt": page.summary[:400],
                    "source_type": "encyclopedia",
                })

            # Try extracting key terms for a second search
            keywords = [w for w in query.split() if len(w) > 4][:3]
            if keywords and len(results) < num_results:
                for kw in keywords:
                    p2 = _wiki.page(kw)
                    if p2.exists() and p2.fullurl not in [r["url"] for r in results]:
                        results.append({
                            "url": p2.fullurl,
                            "title": f"Wikipedia: {p2.title}",
                            "credibility_score": 0.70,
                            "excerpt": p2.summary[:400],
                            "source_type": "encyclopedia",
                        })
                        if len(results) >= num_results:
                            break

            return results

        return await asyncio.to_thread(_run_search)
    except Exception as exc:
        logger.error("Wikipedia search error: %s", exc)
        return []
