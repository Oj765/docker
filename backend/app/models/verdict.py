from pydantic import BaseModel
from typing import List

class VerdictRequest(BaseModel):
    label: str
    confidence: float
    reasoning_chain: List[str]
    evidence_sources: List[str]

class ActionRequest(BaseModel):
    claim_id: str
    action_type: str
    response_text: str
