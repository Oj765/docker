# ml-agent/agent/nodes/output.py  (DIFF — add geo_db insert call)
# Merge into your existing output_node

import asyncio
from agent.state import AgentState

# ── Add to your existing output_node imports ──────────────────────────────────
# from backend.app.services.geo_db import insert_geo_event
# OR call via internal HTTP if ml-agent and backend are separate services:
import httpx, os

BACKEND_URL = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000")


async def output_node(state: AgentState) -> AgentState:
    # ... your existing Kafka publish logic stays unchanged ...

    # ── ADD: write geo event to TimescaleDB via backend internal endpoint ────
    geo = state.get("geo_metadata")
    if geo and geo.get("affected_regions"):
        try:
            async with httpx.AsyncClient(timeout=3) as h:
                await h.post(
                    f"{BACKEND_URL}/internal/geo-event",
                    json={
                        "claim_id": state["claim_id"],
                        "geo":      geo,
                        "verdict":  state.get("verdict", {}),
                    }
                )
        except Exception as e:
            # Non-blocking — geo write failure must never block verdict output
            print(f"[output_node] geo_db write failed (non-fatal): {e}")

    return state


# ── OR if ml-agent and backend share the same process ───────────────────────
# Add this directly inside output_node instead:
#
#   from app.services.geo_db import insert_geo_event
#   geo = state.get("geo_metadata")
#   if geo:
#       asyncio.create_task(insert_geo_event(state["claim_id"], geo, state.get("verdict", {})))
