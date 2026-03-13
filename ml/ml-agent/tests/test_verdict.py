import pytest
from nodes.verdict import VerdictSchema

def test_verdict_schema_validation():
    data = {
        "label": "FALSE",
        "confidence": 0.95,
        "reasoning_chain": ["Step 1: Analyzed text.", "Step 2: Found contradiction."],
        "evidence_sources": [
            {
                "url": "https://who.int/test",
                "title": "Test Title",
                "credibility_score": 1.0,
                "excerpt": "This claim is false."
            }
        ],
        "satire_flag": False
    }
    
    validated = VerdictSchema(**data)
    assert validated.label == "FALSE"
    assert len(validated.evidence_sources) == 1
    assert validated.evidence_sources[0].credibility_score == 1.0
