# ml-agent/nodes/geo_tagger.py
# LangGraph node — tags every claim with geopolitical metadata
# Runs AFTER verdict_node, BEFORE output_node
# Publishes enriched verdict to Kafka: verdict_ready

import os
import asyncio
from typing import Optional
from datetime import datetime

import httpx
from anthropic import AsyncAnthropic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import pycountry

from agent.state import AgentState

client = AsyncAnthropic()
geocoder = Nominatim(user_agent="misinfo-shield-geo", timeout=3)

# ── External reference data ──────────────────────────────────────────────────

ELECTION_CALENDAR_API = os.getenv("ACLED_API_URL", "https://api.acleddata.com/acled/read")
CONFLICT_API_URL       = os.getenv("GDELT_API_URL",  "https://api.gdeltproject.org/api/v2/geo/geo")
WHO_OUTBREAK_API       = os.getenv("WHO_OUTBREAK_URL", "https://www.who.int/api/news/emergencies")

POLITICAL_ALIGNMENT_LABELS = [
    "left", "center-left", "center", "center-right", "right",
    "nationalist", "populist", "religious-conservative", "libertarian", "authoritarian"
]

DEMOGRAPHIC_LABELS = [
    "general public", "elderly", "youth", "rural", "urban",
    "religious community", "ethnic minority", "military/veterans",
    "healthcare workers", "investors/financial"
]

# ── Main node ────────────────────────────────────────────────────────────────

async def geo_tagger_node(state: AgentState) -> AgentState:
    """
    Enriches a verified claim with geopolitical metadata:
    - country_of_origin: where the claim was posted from
    - affected_regions: list of countries/regions the claim targets
    - target_demographic: who this claim is aimed at
    - political_alignment: ideological lean of the claim
    - conflict_zone_overlap: bool — is any affected region in active conflict?
    - election_proximity: list of upcoming elections in affected regions
    - health_emergency_overlap: bool — does this overlap an active WHO event?
    - geo_risk_multiplier: float — amplifies base risk_score
    """
    claim_text  = state.get("translated_text") or state.get("original_text", "")
    source_meta = state.get("source", {})
    verdict     = state.get("verdict", {})

    if not claim_text:
        state["geo_metadata"] = _empty_geo()
        return state

    # Run LLM tagging + external lookups in parallel
    llm_task        = _llm_geo_tag(claim_text, source_meta)
    conflict_task   = _fetch_conflict_zones()
    election_task   = _fetch_election_calendar()
    outbreak_task   = _fetch_who_outbreaks()

    llm_result, conflict_zones, elections, outbreaks = await asyncio.gather(
        llm_task, conflict_task, election_task, outbreak_task,
        return_exceptions=True
    )

    if isinstance(llm_result, Exception):
        llm_result = _empty_llm_geo()

    affected_regions = llm_result.get("affected_regions", [])

    conflict_overlap  = _check_overlap(affected_regions, conflict_zones  if not isinstance(conflict_zones,  Exception) else [])
    election_proximity = _check_elections(affected_regions,             elections    if not isinstance(elections,    Exception) else [])
    health_overlap    = _check_overlap(affected_regions, outbreaks      if not isinstance(outbreaks,     Exception) else [])

    geo_risk_multiplier = _compute_geo_risk(
        conflict_overlap, election_proximity, health_overlap,
        llm_result.get("political_alignment", "center")
    )

    state["geo_metadata"] = {
        "country_of_origin":       llm_result.get("country_of_origin"),
        "affected_regions":        affected_regions,
        "target_demographic":      llm_result.get("target_demographic", "general public"),
        "political_alignment":     llm_result.get("political_alignment", "center"),
        "conflict_zone_overlap":   conflict_overlap,
        "election_proximity":      election_proximity,
        "health_emergency_overlap": health_overlap,
        "geo_risk_multiplier":     geo_risk_multiplier,
        "tagged_at":               datetime.utcnow().isoformat(),
    }

    # Boost risk_score by geo multiplier
    base_risk = verdict.get("risk_score", 0.0)
    state["verdict"]["risk_score"] = min(1.0, round(base_risk * geo_risk_multiplier, 4))
    state["verdict"]["geo_boosted"] = geo_risk_multiplier > 1.0

    return state


# ── LLM geo tagging ──────────────────────────────────────────────────────────

async def _llm_geo_tag(claim_text: str, source_meta: dict) -> dict:
    system_prompt = (
        "You are a geopolitical intelligence analyst. Given a social media claim, "
        "return ONLY valid JSON with no markdown fences. Schema:\n"
        "{\n"
        f'  "country_of_origin": <ISO 3166-1 alpha-2 or null>,\n'
        f'  "affected_regions": [<ISO alpha-2 codes>, ...],\n'
        f'  "target_demographic": <one of: {", ".join(DEMOGRAPHIC_LABELS)}>,\n'
        f'  "political_alignment": <one of: {", ".join(POLITICAL_ALIGNMENT_LABELS)}>\n'
        "}\n"
        "affected_regions = countries whose population this claim is designed to influence. "
        "Be conservative: only include countries with clear relevance. Max 5 countries."
    )

    source_hint = f"\nSource platform: {source_meta.get('platform', 'unknown')}"
    if source_meta.get("account_location"):
        source_hint += f"\nPoster location hint: {source_meta['account_location']}"

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": claim_text + source_hint}]
    )

    import json
    text = response.content[0].text.strip()
    return json.loads(text)


# ── External data fetchers ───────────────────────────────────────────────────

async def _fetch_conflict_zones() -> list[str]:
    """Returns list of ISO alpha-2 country codes currently in active conflict (ACLED)."""
    try:
        async with httpx.AsyncClient(timeout=5) as h:
            r = await h.get(CONFLICT_API_URL, params={
                "key": os.getenv("ACLED_API_KEY", ""),
                "email": os.getenv("ACLED_EMAIL", ""),
                "limit": 500,
                "fields": "country_code",
                "event_date": _last_30_days(),
            })
            data = r.json().get("data", [])
            return list({d["country_code"] for d in data if d.get("country_code")})
    except Exception:
        # Fallback: known active conflict zones (update periodically)
        return ["UA", "PS", "SD", "SO", "YE", "MM", "ET", "LY", "ML", "SY"]


async def _fetch_election_calendar() -> list[dict]:
    """Returns upcoming elections: [{country_code, election_date, days_away}]."""
    try:
        async with httpx.AsyncClient(timeout=5) as h:
            r = await h.get(
                "https://data.opendatasoft.com/api/explore/v2.1/catalog/datasets/elections-calendar/records",
                params={"limit": 100, "where": "election_date >= today()"}
            )
            records = r.json().get("results", [])
            result = []
            for rec in records:
                iso = rec.get("country_iso", "")
                edate = rec.get("election_date", "")
                if iso and edate:
                    try:
                        days = (datetime.fromisoformat(edate) - datetime.utcnow()).days
                        if 0 <= days <= 90:
                            result.append({"country_code": iso.upper(), "election_date": edate, "days_away": days})
                    except Exception:
                        pass
            return result
    except Exception:
        return []


async def _fetch_who_outbreaks() -> list[str]:
    """Returns ISO codes of countries with active WHO health emergencies."""
    try:
        async with httpx.AsyncClient(timeout=5) as h:
            r = await h.get(WHO_OUTBREAK_API, params={"$limit": 50})
            data = r.json() if r.status_code == 200 else []
            codes = []
            for item in data:
                country = item.get("country", "")
                if country:
                    c = pycountry.countries.get(name=country)
                    if c:
                        codes.append(c.alpha_2)
            return codes
    except Exception:
        return []


# ── Overlap checks ────────────────────────────────────────────────────────────

def _check_overlap(affected_regions: list[str], reference: list) -> bool:
    if not affected_regions or not reference:
        return False
    ref_codes = set()
    for item in reference:
        if isinstance(item, str):
            ref_codes.add(item.upper())
        elif isinstance(item, dict):
            ref_codes.add(item.get("country_code", "").upper())
    return any(r.upper() in ref_codes for r in affected_regions)


def _check_elections(affected_regions: list[str], elections: list[dict]) -> list[dict]:
    if not affected_regions or not elections:
        return []
    region_set = {r.upper() for r in affected_regions}
    return [e for e in elections if e.get("country_code", "").upper() in region_set]


def _compute_geo_risk(
    conflict: bool,
    elections: list,
    health: bool,
    alignment: str
) -> float:
    multiplier = 1.0
    if conflict:
        multiplier += 0.35
    if elections:
        # Closer election = higher multiplier
        min_days = min(e.get("days_away", 90) for e in elections)
        if min_days <= 7:
            multiplier += 0.40
        elif min_days <= 30:
            multiplier += 0.25
        elif min_days <= 90:
            multiplier += 0.10
    if health:
        multiplier += 0.20
    # Extreme alignments carry more risk
    if alignment in ("nationalist", "authoritarian", "populist"):
        multiplier += 0.10
    return round(min(multiplier, 2.5), 3)


def _empty_geo() -> dict:
    return {
        "country_of_origin": None, "affected_regions": [],
        "target_demographic": "general public", "political_alignment": "center",
        "conflict_zone_overlap": False, "election_proximity": [],
        "health_emergency_overlap": False, "geo_risk_multiplier": 1.0,
        "tagged_at": datetime.utcnow().isoformat(),
    }

def _empty_llm_geo() -> dict:
    return {"country_of_origin": None, "affected_regions": [],
            "target_demographic": "general public", "political_alignment": "center"}

def _last_30_days() -> str:
    from datetime import timedelta
    d = datetime.utcnow() - timedelta(days=30)
    return d.strftime("%Y-%m-%d")
