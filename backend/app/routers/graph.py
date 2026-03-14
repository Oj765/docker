from fastapi import APIRouter, Request
from typing import Optional
from datetime import datetime, timezone, timedelta

router = APIRouter(tags=["Graph"])

def _time_filter(timeRange: str):
    now = datetime.now(timezone.utc)
    mapping = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
    hours = mapping.get(timeRange, 24)
    return now - timedelta(hours=hours)

@router.get("/graph")
async def get_graph_data(
    request: Request,
    timeRange: Optional[str] = "24h",
    platform: Optional[str] = "all",
    severity: Optional[str] = "all"
):
    """Build a narrative graph from real MongoDB claims."""
    db = request.app.mongodb
    since = _time_filter(timeRange)

    # Build query filter
    query: dict = {"created_at": {"$gte": since}}
    if platform and platform != "all":
        query["source.platform"] = platform
    if severity and severity != "all":
        sev_map = {"low": (0, 0.3), "medium": (0.3, 0.6), "high": (0.6, 0.85), "critical": (0.85, 1.0)}
        lo, hi = sev_map.get(severity, (0, 1.0))
        query["risk_score"] = {"$gte": lo, "$lt": hi}

    cursor = db.claims.find(query, {
        "claim_id": 1, "original_text": 1, "source": 1,
        "verdict": 1, "risk_score": 1, "parent_claim_id": 1, "mutation_depth": 1
    }).sort("created_at", -1).limit(100)
    claims = await cursor.to_list(length=100)

    nodes = []
    links = []
    seen_accounts = set()

    for c in claims:
        claim_id = c.get("claim_id", str(c.get("_id", "")))
        score = c.get("risk_score", 0.0)
        verdict_label = (c.get("verdict") or {}).get("label", "UNVERIFIED")
        plat = (c.get("source") or {}).get("platform", "unknown")
        account_id = (c.get("source") or {}).get("account_id", "unknown")
        text = (c.get("original_text") or "")[:60]

        # Risk severity
        if score >= 0.85: sev = "CRITICAL"
        elif score >= 0.6: sev = "HIGH"
        elif score >= 0.3: sev = "MEDIUM"
        else: sev = "LOW"

        # Claim node
        nodes.append({
            "id": claim_id, "label": text, "type": "claim",
            "platform": plat, "verdict": verdict_label,
            "severity": sev, "risk_score": score
        })

        # Account node (deduplicated)
        if account_id and account_id not in seen_accounts:
            seen_accounts.add(account_id)
            nodes.append({
                "id": f"acc_{account_id}", "label": account_id,
                "type": "account", "platform": plat, "followers": 0
            })

        # Account → Claim link
        if account_id:
            links.append({"source": f"acc_{account_id}", "target": claim_id, "type": "POSTED"})

        # Mutation link (parent → child)
        parent = c.get("parent_claim_id")
        if parent:
            links.append({"source": parent, "target": claim_id, "type": "MUTATION"})

    # Fallback if DB is empty — return demo data so the graph renders
    if not nodes:
        nodes = [
            {"id": "demo_acc1", "label": "Demo Source", "type": "account", "platform": "twitter", "followers": 5000},
            {"id": "demo_claim1", "label": "Vaccine causes 5G activation (demo)", "type": "claim", "platform": "twitter", "verdict": "FALSE", "severity": "HIGH", "risk_score": 0.82},
            {"id": "demo_claim2", "label": "Moon landing was faked (demo)", "type": "claim", "platform": "facebook", "verdict": "FALSE", "severity": "CRITICAL", "risk_score": 0.91},
            {"id": "demo_acc2", "label": "Demo Bot Network", "type": "account", "platform": "facebook", "followers": 12000},
        ]
        links = [
            {"source": "demo_acc1", "target": "demo_claim1", "type": "POSTED"},
            {"source": "demo_acc2", "target": "demo_claim2", "type": "POSTED"},
            {"source": "demo_claim1", "target": "demo_claim2", "type": "MUTATION"},
        ]

    return {"success": True, "data": {"nodes": nodes, "links": links}}


@router.post("/alerts")
async def trigger_alert(payload: dict):
    return {"status": "Alert triggered manually"}