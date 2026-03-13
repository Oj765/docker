import pytest
import asyncio
from agent.graph import graph
from agent.state import AgentState

@pytest.mark.asyncio
async def test_full_pipeline_true_claim():
    initial_state = {
        "claim_id": "test_claim_001",
        "original_text": "Water boils at 100 degrees Celsius at sea level.",
        "source_platform": "twitter",
        "media_urls": [],
        "posted_at": "2026-03-13T10:00:00Z"
    }
    
    final_state = await graph.ainvoke(initial_state)
    
    assert final_state is not None
    assert "verdict" in final_state
    
    verdict = final_state["verdict"]
    assert verdict["label"] in ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]
    assert 0.0 <= verdict["confidence"] <= 1.0
    assert 0.0 <= verdict["risk_score"] <= 1.0
    assert isinstance(verdict["reasoning_chain"], list)
    assert len(verdict["reasoning_chain"]) > 0
    assert isinstance(verdict["evidence_sources"], list)
