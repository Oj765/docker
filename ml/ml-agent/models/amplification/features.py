from typing import Any, Dict


def build_amplification_features(state: Dict[str, Any]) -> Dict[str, float]:
    engagement = state.get("engagement", {}) or {}
    likes = float(engagement.get("likes", 0) or 0)
    shares = float(engagement.get("shares", 0) or 0)
    comments = float(engagement.get("comments", 0) or 0)
    followers = float(state.get("source_followers", 0) or 0)

    avg_rt_rate = 0.0
    if followers > 0:
        avg_rt_rate = min(shares / max(followers, 1.0), 1.0)

    text = (state.get("original_text") or "").lower()
    sentiment = 0.2 if any(token in text for token in ["danger", "breaking", "urgent", "shocking"]) else 0.0
    centrality = min((shares + comments) / max(followers + 1.0, 1.0), 1.0)

    return {
        "account_followers": followers,
        "avg_rt_rate": avg_rt_rate,
        "sentiment": sentiment,
        "time_of_day": 12.0,
        "centrality": centrality,
        "engagement_volume": likes + shares + comments,
    }
