from fastapi import APIRouter
from typing import Optional

router = APIRouter(tags=["Graph"])

@router.get("/graph")
async def get_graph_data(timeRange: Optional[str] = "24h", platform: Optional[str] = "all", severity: Optional[str] = "all"):
    # Return mock data for now
    return {
        "nodes": [
            {"id": "user1", "label": "User A", "type": "account", "platform": "twitter", "followers": 1000},
            {"id": "claim1", "label": "Fake Claim", "type": "claim", "verdict": "FALSE", "severity": "HIGH"}
        ],
        "links": [
            {"source": "user1", "target": "claim1", "type": "POSTED"}
        ]
    }

@router.post("/alerts")
async def trigger_alert(payload: dict):
    return {"status": "Alert triggered manually"}