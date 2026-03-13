from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class Source(BaseModel):
    platform: str
    account_id: str
    post_url: str
    posted_at: datetime

class Media(BaseModel):
    type: str
    url: str
    ocr_text: Optional[str] = None
    transcription: Optional[str] = None
    deepfake_score: Optional[float] = None

class Action(BaseModel):
    type: str
    response_text: str
    posted_at: datetime
    reviewer_id: str

class VerdictData(BaseModel):
    label: str
    confidence: float
    reasoning_chain: List[str]
    evidence_sources: List[str]

class Claim(BaseModel):
    claim_id: str
    original_text: str
    translated_text: Optional[str] = None
    language: str
    source: Source
    media: Optional[Media] = None
    embedding_ref: Optional[str] = None
    parent_claim_id: Optional[str] = None
    mutation_depth: Optional[int] = 0
    verdict: Optional[VerdictData] = None
    risk_score: Optional[float] = 0.0
    predicted_6h_reach: Optional[int] = 0
    actual_reach: Optional[int] = 0
    action: Optional[Action] = None
    verdict_expires_at: Optional[datetime] = None
    category: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
