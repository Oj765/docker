from pydantic import BaseModel
from typing import Any, Dict

class WebhookPayload(BaseModel):
    alert_type: str
    severity: str
    message: str
    metadata: Dict[str, Any] = {}
