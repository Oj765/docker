"""Enrichment node: predicts region, time context, and topic tags from claim text and evidence."""

import logging
import re
from typing import Any, Dict, List

from agent.state import AgentState

logger = logging.getLogger(__name__)

# Region keyword mapping
REGION_KEYWORDS: Dict[str, List[str]] = {
    "India": ["india", "modi", "bjp", "congress", "delhi", "mumbai", "rupee", "aadhar",
              "aadhaar", "pmo", "niti aayog", "lok sabha", "rajya sabha", "ndtv",
              "data.gov.in", "ayush", "icmr", "aiims"],
    "United States": ["usa", "u.s.", "united states", "trump", "biden", "fda", "cdc",
                      "white house", "congress", "senate", "democrat", "republican",
                      "washington", "new york", "california", "fbi", "cia"],
    "United Kingdom": ["uk", "britain", "british", "london", "nhs", "parliament",
                       "bbc", "downing street"],
    "China": ["china", "chinese", "beijing", "ccp", "xi jinping", "wuhan"],
    "Europe": ["eu", "european", "brussels", "france", "germany", "berlin", "paris"],
    "Middle East": ["israel", "palestine", "gaza", "iran", "saudi", "dubai"],
    "Global": ["who", "united nations", "un", "world", "global", "international",
               "pandemic", "climate"],
}

TOPIC_KEYWORDS: Dict[str, List[str]] = {
    "health": ["vaccine", "virus", "covid", "cure", "medicine", "disease", "hospital",
               "doctor", "health", "bleach", "ivermectin", "drug", "pharma", "cancer",
               "who", "cdc", "icmr"],
    "politics": ["election", "vote", "ballot", "government", "minister", "president",
                 "parliament", "law", "policy", "party", "corruption"],
    "science": ["5g", "radiation", "climate", "earth", "nasa", "space", "research",
                "study", "scientist", "dna", "gmo"],
    "economy": ["gdp", "inflation", "rupee", "dollar", "stock", "market", "tax",
                "economy", "trade", "export", "import"],
    "security": ["terrorism", "attack", "bomb", "riot", "army", "military", "war",
                 "border", "weapons"],
    "technology": ["ai", "artificial intelligence", "smartphone", "app", "data",
                   "privacy", "hack", "cyber"],
}

TIME_KEYWORDS: Dict[str, List[str]] = {
    "breaking": ["breaking", "just in", "happening now", "alert", "urgent"],
    "recent": ["today", "yesterday", "this week", "hours ago", "just", "latest", "new"],
    "ongoing": ["continues", "ongoing", "still", "developing", "update"],
    "historical": ["years ago", "in 2020", "in 2019", "history", "historically",
                   "decade", "century"],
}


def _match_keywords(text: str, keyword_map: Dict[str, List[str]]) -> Dict[str, int]:
    """Count keyword matches per category."""
    text_lower = text.lower()
    scores: Dict[str, int] = {}
    for category, keywords in keyword_map.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > 0:
            scores[category] = count
    return scores


async def enrich_node(state: AgentState) -> Dict[str, Any]:
    """Predict region, time context, and topic from claim text and evidence."""
    text = state.get("original_text", "")
    evidence = list(state.get("evidence", []))
    reasoning = list(state.get("reasoning_chain", []))

    # Combine claim text + evidence excerpts for richer analysis
    combined = text
    for ev in evidence:
        combined += " " + ev.get("title", "") + " " + ev.get("excerpt", "")
        combined += " " + ev.get("url", "")

    # Region prediction
    region_scores = _match_keywords(combined, REGION_KEYWORDS)
    if region_scores:
        sorted_regions = sorted(region_scores.items(), key=lambda x: x[1], reverse=True)
        primary_region = sorted_regions[0][0]
        all_regions = [r for r, _ in sorted_regions]
        region_conf = min(sorted_regions[0][1] / 5.0, 1.0)
    else:
        primary_region = "Unknown"
        all_regions = ["Unknown"]
        region_conf = 0.0

    # Topic prediction
    topic_scores = _match_keywords(combined, TOPIC_KEYWORDS)
    topic_tags = [t for t, _ in sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)]
    if not topic_tags:
        topic_tags = ["general"]

    # Time context
    time_scores = _match_keywords(combined, TIME_KEYWORDS)
    if time_scores:
        time_context = max(time_scores, key=time_scores.get)
    else:
        time_context = "recent"

    geo_info = {
        "predicted_region": primary_region,
        "predicted_regions": all_regions[:3],
        "region_confidence": round(region_conf, 2),
        "time_context": time_context,
        "topic_tags": topic_tags[:4],
    }

    reasoning.append(
        f"Enrich: Predicted region={primary_region} (conf={region_conf:.2f}), "
        f"topics={topic_tags[:3]}, time_context={time_context}"
    )

    logger.info("Enrichment: region=%s, topics=%s", primary_region, topic_tags[:3])

    return {
        "geo_info": geo_info,
        "reasoning_chain": reasoning,
    }
