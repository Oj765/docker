# backend/app/routers/internal.py
# Internal endpoints — NOT exposed publicly, only called by ml-agent service
# Mount in main.py: app.include_router(internal_router, prefix="/internal")

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from app.services.geo_db import insert_geo_event

router = APIRouter()

INTERNAL_SECRET = os.getenv("INTERNAL_SECRET", "changeme-internal-secret")


class GeoEventPayload(BaseModel):
    claim_id: str
    geo:      dict
    verdict:  dict


@router.post("/geo-event", include_in_schema=False)
async def receive_geo_event(
    payload: GeoEventPayload,
    x_internal_secret: Optional[str] = Header(None)
):
    if x_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    await insert_geo_event(payload.claim_id, payload.geo, payload.verdict)
    return {"ok": True}
