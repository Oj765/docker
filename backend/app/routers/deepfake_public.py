# backend/app/routers/deepfake_public.py
# Public (auth-gated) endpoint for the dashboard deepfake feed.
# Mount: app.include_router(deepfake_public_router, prefix="/deepfake", tags=["deepfake"])

from fastapi import APIRouter, Query, Request
from app.services.deepfake_db import get_flagged_claims

router = APIRouter()


@router.get("/flagged")
async def flagged_claims(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    skip:  int = Query(0,  ge=0),
):
    """
    Returns claims where media.deepfake_flagged = true,
    sorted by risk_score desc. Used by the DeepfakeFeed dashboard component.
    """
    data  = await get_flagged_claims(request.app.mongodb, limit, skip)
    return {"success": True, "data": data, "count": len(data)}
