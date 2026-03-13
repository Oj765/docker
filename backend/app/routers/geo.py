# backend/app/routers/geo.py
# Mount in main.py: app.include_router(geo_router, prefix="/geo", tags=["geo"])

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.services.geo_db import (
    get_heatmap_data,
    get_timeline,
    get_alignment_breakdown,
)
from app.db.mongo import get_db   # your existing motor db accessor

router = APIRouter()


# ── Response models ───────────────────────────────────────────────────────────

class HeatmapCountry(BaseModel):
    country_code:    str
    total_claims:    int
    avg_risk:        float
    max_risk:        float
    conflict_claims: int
    health_claims:   int

class HeatmapResponse(BaseModel):
    success:    bool
    data:       list[HeatmapCountry]
    hours:      int
    generated:  str

class TimelinePoint(BaseModel):
    bucket:         str
    claim_count:    int
    avg_risk:       float
    avg_multiplier: float

class CountryDetailResponse(BaseModel):
    success:              bool
    country_code:         str
    timeline:             list[TimelinePoint]
    alignment_breakdown:  list[dict]
    active_elections:     list[dict]
    recent_claims:        list[dict]

class GeoFilterParams(BaseModel):
    country_code:       Optional[str]  = None
    political_alignment: Optional[str] = None
    conflict_only:      bool           = False
    election_window:    Optional[int]  = None   # days
    health_only:        bool           = False
    limit:              int            = 50
    skip:               int            = 0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/heatmap", response_model=HeatmapResponse)
async def heatmap(hours: int = Query(24, ge=1, le=168)):
    """
    World heatmap data — per-country risk aggregates.
    hours: lookback window (1-168). Default 24.
    Used by the frontend Leaflet/D3 choropleth map.
    """
    data = await get_heatmap_data(hours)
    return {
        "success":   True,
        "data":      data,
        "hours":     hours,
        "generated": datetime.utcnow().isoformat(),
    }


@router.get("/country/{country_code}", response_model=CountryDetailResponse)
async def country_detail(country_code: str, days: int = Query(7, ge=1, le=90)):
    """
    Full geo detail for a single country:
    - risk timeline (daily)
    - political alignment breakdown
    - active election proximity
    - 10 most recent claims targeting this country
    """
    code = country_code.upper()
    db   = await get_db()

    timeline,  alignment = await asyncio.gather(
        get_timeline(code, days),
        get_alignment_breakdown(code),
    )

    # Recent claims from MongoDB
    cursor = db.claims.find(
        {"geo_metadata.affected_regions": code},
        {"claim_id": 1, "original_text": 1, "verdict": 1, "geo_metadata": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10)
    recent = await cursor.to_list(length=10)
    for doc in recent:
        doc.pop("_id", None)

    # Active elections from geo_metadata of recent claims
    elections = []
    for doc in recent:
        prox = doc.get("geo_metadata", {}).get("election_proximity", [])
        for e in prox:
            if e.get("country_code", "").upper() == code and e not in elections:
                elections.append(e)

    return {
        "success":             True,
        "country_code":        code,
        "timeline":            timeline,
        "alignment_breakdown": alignment,
        "active_elections":    elections[:5],
        "recent_claims":       recent,
    }


@router.post("/filter")
async def filter_claims(params: GeoFilterParams):
    """
    Filtered claim list by geo criteria.
    Used by the threat intelligence table on the dashboard.
    """
    db    = await get_db()
    query: dict = {}

    if params.country_code:
        query["geo_metadata.affected_regions"] = params.country_code.upper()
    if params.political_alignment:
        query["geo_metadata.political_alignment"] = params.political_alignment
    if params.conflict_only:
        query["geo_metadata.conflict_zone_overlap"] = True
    if params.health_only:
        query["geo_metadata.health_emergency_overlap"] = True
    if params.election_window is not None:
        query["geo_metadata.election_proximity"] = {
            "$elemMatch": {"days_away": {"$lte": params.election_window}}
        }

    cursor = db.claims.find(query).sort("created_at", -1).skip(params.skip).limit(params.limit)
    total  = await db.claims.count_documents(query)
    docs   = await cursor.to_list(length=params.limit)
    for d in docs:
        d.pop("_id", None)

    return {"success": True, "data": docs, "total": total, "skip": params.skip, "limit": params.limit}


@router.get("/summary")
async def geo_summary():
    """
    Dashboard summary cards:
    - total countries affected (24h)
    - highest risk country
    - active conflict overlaps
    - election proximity alerts
    - health emergency overlaps
    """
    data = await get_heatmap_data(hours=24)
    if not data:
        return {"success": True, "data": _empty_summary()}

    highest = max(data, key=lambda x: x["avg_risk"]) if data else {}
    conflict_countries  = [d["country_code"] for d in data if d["conflict_claims"] > 0]
    health_countries    = [d["country_code"] for d in data if d["health_claims"]   > 0]

    return {
        "success": True,
        "data": {
            "countries_affected":   len(data),
            "total_claims_24h":     sum(d["total_claims"] for d in data),
            "highest_risk_country": highest.get("country_code"),
            "highest_risk_score":   round(highest.get("avg_risk", 0), 3),
            "conflict_countries":   conflict_countries,
            "health_countries":     health_countries,
            "generated":            datetime.utcnow().isoformat(),
        }
    }


def _empty_summary():
    return {
        "countries_affected": 0, "total_claims_24h": 0,
        "highest_risk_country": None, "highest_risk_score": 0.0,
        "conflict_countries": [], "health_countries": [],
        "generated": datetime.utcnow().isoformat(),
    }


import asyncio  # needed for asyncio.gather in country_detail
