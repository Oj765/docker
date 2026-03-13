# backend/app/routers/deepfake.py
# Internal endpoints called by ml-agent. NOT public.
# Mount in main.py:  app.include_router(deepfake_router, prefix="/internal/deepfake")

import os
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.multimodal.deepfake_scorer import score_video_url, score_image_url
from app.db.mongo import get_db

router = APIRouter()
INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "changeme-internal-secret")


class DeepfakeRequest(BaseModel):
    media_url: str
    claim_id:  str


def _auth(secret: Optional[str]):
    if secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Video endpoint ────────────────────────────────────────────────────────────

@router.post("/video", include_in_schema=False)
async def deepfake_video(
    payload: DeepfakeRequest,
    x_internal_secret: Optional[str] = Header(None),
):
    _auth(x_internal_secret)
    result = await score_video_url(payload.media_url)
    await _write_to_mongo(payload.claim_id, result)
    return result


# ── Image endpoint ────────────────────────────────────────────────────────────

@router.post("/image", include_in_schema=False)
async def deepfake_image(
    payload: DeepfakeRequest,
    x_internal_secret: Optional[str] = Header(None),
):
    _auth(x_internal_secret)
    result = await score_image_url(payload.media_url)
    await _write_to_mongo(payload.claim_id, result)
    return result


# ── MongoDB writer ────────────────────────────────────────────────────────────

async def _write_to_mongo(claim_id: str, result: dict):
    """
    Writes deepfake result into the claim's media subdocument.
    Uses MongoDB $set so it merges with existing media fields.

    Resulting document path:  claims.media.deepfake_score
                              claims.media.deepfake_flagged
                              claims.media.deepfake_model
                              claims.media.frames_analysed
                              claims.media.frame_scores
                              claims.media.deepfake_scored_at
    """
    db = await get_db()
    await db.claims.update_one(
        {"claim_id": claim_id},
        {"$set": {
            "media.deepfake_score":     result.get("deepfake_score", 0.0),
            "media.deepfake_flagged":   result.get("is_flagged", False),
            "media.deepfake_model":     result.get("model", ""),
            "media.frames_analysed":    result.get("frames_analysed", 0),
            "media.frame_scores":       result.get("frame_scores", []),
            "media.deepfake_scored_at": datetime.utcnow().isoformat(),
            "media.deepfake_error":     result.get("error"),
        }},
        upsert=False,  # only update existing claims — don't create ghost docs
    )
