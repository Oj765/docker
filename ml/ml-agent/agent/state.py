from typing import Any, Dict, List, NotRequired, Optional, TypedDict


class VerdictSource(TypedDict):
    url: str
    title: str
    credibility_score: float
    excerpt: str


class GeoInfo(TypedDict, total=False):
    predicted_region: str      # e.g. "India", "United States", "Global"
    predicted_regions: List[str]
    region_confidence: float
    time_context: str          # e.g. "recent", "historical", "ongoing"
    topic_tags: List[str]      # e.g. ["health", "politics", "science"]


class NarrativeNode(TypedDict, total=False):
    account_id: str
    platform: str
    claim_id: str
    linked_claims: List[str]
    campaign_id: Optional[str]


class VerdictInfo(TypedDict):
    claim_id: str
    label: str
    confidence: float
    risk_score: float
    reasoning_chain: List[str]
    evidence_sources: List[VerdictSource]
    satire_flag: bool
    language: str
    mutation_of: Optional[str]
    predicted_6h_reach: int
    severity_rating: str
    geo_info: GeoInfo
    narrative: NarrativeNode
    processed_at: str


class EngagementInfo(TypedDict, total=False):
    likes: int
    shares: int
    comments: int


class AgentState(TypedDict, total=False):
    # --- Input (Kafka raw_posts format) ---
    claim_id: str
    original_text: str
    source_platform: str          # twitter | reddit | telegram | facebook | web
    source_account_id: str
    source_post_url: str
    source_followers: int
    media_urls: List[str]
    engagement: EngagementInfo
    posted_at: str                 # ISO-8601

    # --- NLP & Translation ---
    language: str
    translated_text: Optional[str]
    atomic_claims: List[str]

    # --- Evidence ---
    evidence: List[Dict[str, Any]]

    # --- Scoring & Dedup ---
    mutation_of: Optional[str]
    mutation_depth: int
    satire_flag: bool
    confidence: float
    risk_score: float
    predicted_6h_reach: int

    # --- Enrichment ---
    geo_info: GeoInfo
    narrative: NarrativeNode

    # --- Output ---
    verdict: Optional[VerdictInfo]
    reasoning_chain: List[str]
    should_respond: bool
    review_required: bool
    response_text: NotRequired[str]
