import asyncio
import logging
import re

import httpx

logger = logging.getLogger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


def _score_source(title: str, url: str) -> float:
    trusted = ["reuters", "apnews", "bbc", "aljazeera", "ndtv", "thehindu",
               "indianexpress", "hindustantimes", "timesofindia"]
    lower = (title + url).lower()
    if any(t in lower for t in trusted):
        return 0.85
    return 0.65


async def search_google_news(query: str, num_results: int = 4) -> list:
    """Scrape Google News RSS for recent news articles. Free, no API key.

    Google News RSS is publicly accessible and returns recent articles
    from major news outlets matching the query. Great for checking whether
    a claim has been reported on by credible media.
    """
    logger.info("Querying Google News RSS for: %s", query[:80])

    try:
        url = GOOGLE_NEWS_RSS.format(query=query.replace(" ", "+"))

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, headers={"User-Agent": "MisinfoShield/1.0"})
            resp.raise_for_status()
            xml = resp.text

        results = []
        # Simple XML parsing (no lxml dependency needed)
        items = re.findall(r"<item>(.*?)</item>", xml, re.DOTALL)

        for item_xml in items[:num_results]:
            title_match = re.search(r"<title>(.*?)</title>", item_xml)
            link_match = re.search(r"<link>(.*?)</link>", item_xml)
            desc_match = re.search(r"<description>(.*?)</description>", item_xml)
            source_match = re.search(r"<source[^>]*>(.*?)</source>", item_xml)

            title = title_match.group(1) if title_match else ""
            link = link_match.group(1) if link_match else ""
            desc = desc_match.group(1) if desc_match else ""
            source = source_match.group(1) if source_match else ""

            # Clean HTML entities
            for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&#39;", "'"), ("&quot;", '"')]:
                title = title.replace(entity, char)
                desc = desc.replace(entity, char)

            # Strip any remaining HTML tags from description
            desc = re.sub(r"<[^>]+>", "", desc)

            if title and link:
                full_title = f"{title} ({source})" if source else title
                results.append({
                    "url": link,
                    "title": full_title,
                    "credibility_score": _score_source(full_title, link),
                    "excerpt": desc[:300] if desc else f"News article from {source}",
                    "source_type": "news",
                })

        logger.info("Google News returned %d results", len(results))
        return results

    except Exception as exc:
        logger.error("Google News RSS error: %s", exc)
        return []
