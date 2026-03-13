# ml-agent/nodes/deepfake_node.py
# LangGraph node — runs AFTER ingest_node, BEFORE extract_node
# Only activates for video/image media types. Writes deepfake_score to state.

import os
import asyncio
from agent.state import AgentState

BACKEND_URL     = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "changeme-internal-secret")

# Score threshold above which claim gets satire_flag=False but deepfake_flag=True
DEEPFAKE_THRESHOLD = float(os.getenv("DEEPFAKE_CONFIDENCE_THRESHOLD", "0.65"))


async def deepfake_node(state: AgentState) -> AgentState:
    """
    Checks media.type — if video or image, calls the deepfake scorer service.
    Writes result into state["media"] and boosts risk_score if flagged.
    Skips silently for text-only claims.
    """
    media = state.get("media")
    if not media:
        return state

    media_type = (media.get("type") or "").lower()
    media_url  = media.get("url")

    if not media_url or media_type not in ("video", "image"):
        return state

    import httpx
    try:
        async with httpx.AsyncClient(timeout=120) as h:
            endpoint = (
                "/internal/deepfake/video"
                if media_type == "video"
                else "/internal/deepfake/image"
            )
            r = await h.post(
                f"{BACKEND_URL}{endpoint}",
                json={"media_url": media_url, "claim_id": state["claim_id"]},
                headers={"x-internal-secret": INTERNAL_SECRET},
            )
            result = r.json()

        state["media"]["deepfake_score"]    = result.get("deepfake_score", 0.0)
        state["media"]["deepfake_flagged"]  = result.get("is_flagged", False)
        state["media"]["deepfake_model"]    = result.get("model", "")
        state["media"]["frames_analysed"]   = result.get("frames_analysed", 0)

        # If deepfake detected, boost the verdict risk_score
        if result.get("is_flagged"):
            verdict = state.get("verdict", {})
            current = verdict.get("risk_score", 0.0)
            # Additive boost: deepfake_score contributes 40% weight
            boosted = min(1.0, current + result["deepfake_score"] * 0.4)
            state.setdefault("verdict", {})["risk_score"] = round(boosted, 4)
            state.setdefault("verdict", {})["deepfake_boosted"] = True

    except Exception as e:
        # Non-blocking: deepfake failure must never break the pipeline
        state["media"]["deepfake_score"]   = 0.0
        state["media"]["deepfake_flagged"] = False
        state["media"]["deepfake_error"]   = str(e)

    return state
