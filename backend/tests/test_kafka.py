import pytest
from app.models.claim import Claim
from datetime import datetime

def test_claim_model():
    claim_data = {
        "claim_id": "test_123",
        "original_text": "This is a fake post",
        "language": "en",
        "source": {
            "platform": "twitter",
            "account_id": "user123",
            "post_url": "http://x.com",
            "posted_at": "2023-01-01T00:00:00Z"
        }
    }
    claim = Claim(**claim_data)
    assert claim.claim_id == "test_123"
    assert claim.original_text == "This is a fake post"
