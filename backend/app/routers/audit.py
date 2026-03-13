from fastapi import APIRouter, Depends, Request, Query
from typing import Optional
from app.services.auth import require_role

router = APIRouter(prefix="/audit", tags=["audit"])

@router.get("/")
async def get_audit_log(
    request: Request,
    user: dict = Depends(require_role(["admin", "operator"])),
    reviewer_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    skip: int = Query(0)
):
    db = request.app.mongodb

    # Build filter dynamically based on query params
    filters = {"action": {"$exists": True}}
    if reviewer_id:
        filters["action.reviewer_id"] = reviewer_id
    if action_type:
        filters["action.type"] = action_type

    cursor = db.claims.find(filters, {"_id": 0, "claim_id": 1, "action": 1, "created_at": 1})
    cursor = cursor.sort("action.posted_at", -1).skip(skip).limit(limit)

    results = await cursor.to_list(length=limit)

    return {
        "success": True,
        "data": results,
        "error": None
    }