from fastapi import APIRouter, Request, Query
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.get("/")
async def list_campaigns(
    request: Request,
    category: Optional[str] = Query(None),
    min_risk: Optional[float] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0)
):
    db = request.app.mongodb

    # Build filter
    filters = {"parent_claim_id": {"$exists": True}}
    if category:
        filters["category"] = category
    if min_risk:
        filters["risk_score"] = {"$gte": min_risk}

    # Group by parent_claim_id to detect narrative campaigns
    pipeline = [
        {"$match": filters},
        {"$group": {
            "_id": "$parent_claim_id",
            "claim_count": {"$sum": 1},
            "avg_risk_score": {"$avg": "$risk_score"},
            "max_predicted_reach": {"$max": "$predicted_6h_reach"},
            "categories": {"$addToSet": "$category"},
            "platforms": {"$addToSet": "$source.platform"},
            "latest_claim_at": {"$max": "$created_at"}
        }},
        {"$sort": {"avg_risk_score": -1}},
        {"$skip": skip},
        {"$limit": limit}
    ]

    cursor = db.claims.aggregate(pipeline)
    results = await cursor.to_list(length=limit)

    # Serialize ObjectId if present
    for r in results:
        r["parent_claim_id"] = r.pop("_id")

    return {
        "success": True,
        "data": results,
        "error": None
    }


@router.get("/{campaign_id}/graph")
async def get_campaign_graph(
    campaign_id: str,
    request: Request
):
    db = request.app.mongodb

    # Fetch all mutations of this parent claim
    cursor = db.claims.find(
        {"parent_claim_id": campaign_id},
        {"_id": 0, "claim_id": 1, "parent_claim_id": 1,
         "mutation_depth": 1, "source": 1, "risk_score": 1,
         "verdict": 1, "created_at": 1}
    )
    claims = await cursor.to_list(length=200)

    # Build D3-compatible nodes + links
    nodes = [{"id": c["claim_id"], "depth": c.get("mutation_depth", 0),
               "platform": c.get("source", {}).get("platform"),
               "risk_score": c.get("risk_score")} for c in claims]

    links = [{"source": c["parent_claim_id"], "target": c["claim_id"]}
             for c in claims if c.get("parent_claim_id")]

    return {
        "success": True,
        "data": {"nodes": nodes, "links": links},
        "error": None
    }