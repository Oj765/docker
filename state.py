# ml-agent/agent/state.py  (ADD these fields to your existing AgentState TypedDict)
# Only the new geo-related fields are shown — merge into your existing state.py

from typing import TypedDict, Optional, Any

class GeoMetadata(TypedDict):
    country_of_origin:        Optional[str]   # ISO alpha-2 or None
    affected_regions:         list[str]        # ISO alpha-2 list
    target_demographic:       str
    political_alignment:      str
    conflict_zone_overlap:    bool
    election_proximity:       list[dict]       # [{country_code, election_date, days_away}]
    health_emergency_overlap: bool
    geo_risk_multiplier:      float
    tagged_at:                str              # ISO8601


# ── Merge into your existing AgentState ─────────────────────────────────────
# Add this field to your current AgentState TypedDict:
#
#   geo_metadata: Optional[GeoMetadata]
#
# Full AgentState shown below for reference:

class AgentState(TypedDict):
    # ── existing fields ──
    claim_id:         str
    original_text:    str
    translated_text:  Optional[str]
    language:         str
    source:           dict                # {platform, account_id, post_url, posted_at, account_location}
    media:            Optional[dict]
    embedding_ref:    Optional[str]
    parent_claim_id:  Optional[str]
    mutation_depth:   int
    verdict:          dict                # {label, confidence, risk_score, reasoning_chain, evidence_sources, ...}
    satire_flag:      bool

    # ── new geo field ──
    geo_metadata:     Optional[GeoMetadata]
