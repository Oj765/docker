import sys
import os
import uuid
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, List

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["analyze"])

# Add the ML agent to sys.path so we can import from it
ML_AGENT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml", "ml-agent")
)
if ML_AGENT_PATH not in sys.path:
    sys.path.insert(0, ML_AGENT_PATH)

FEDNET_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if FEDNET_PATH not in sys.path:
    sys.path.insert(0, FEDNET_PATH)

from federated_network.integration import FederatedNetworkAdapter

fednet_adapter = FederatedNetworkAdapter(
    base_url=os.getenv("FEDNET_URL", "http://127.0.0.1:8000"),
    node_id=os.getenv("FEDNET_NODE_ID", "node-local")
)


class AnalyzeRequest(BaseModel):
    text: str
    platform: str = "manual"
    account_id: str = "api_user"
    post_url: str = "https://manual.entry"
    media_urls: List[str] = []
    language: Optional[str] = None  # auto-detect if None


class AnalyzeResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


@router.post("/", response_model=AnalyzeResponse)
async def analyze_claim(body: AnalyzeRequest, request: Request):
    """
    Run a claim through the full ML LangGraph pipeline:
    translate → extract → dedup → verify → score → guardrail → verdict → output
    
    Returns the structured verdict and saves to MongoDB.
    Also publishes to Kafka verdict_ready topic (via output_node).
    """
    claim_id = f"api-{uuid.uuid4().hex[:12]}"

    # Check Redis dedup first before running expensive ML pipeline
    from app.services.redis_dedup import redis_dedup
    # Use a hash of the text as the dedup key for manual submissions
    import hashlib
    text_hash = hashlib.sha256(body.text.encode()).hexdigest()[:16]
    is_dup = await redis_dedup.is_duplicate(f"text:{text_hash}")
    if is_dup:
        logger.info(f"Duplicate claim text detected via Redis — seeking existing MongoDB record")
        db = request.app.mongodb
        doc = await db.claims.find_one({"original_text": body.text}, {"_id": 0})
        if doc:
            return AnalyzeResponse(
                success=True,
                data={
                    "claim_id": doc.get("claim_id"),
                    "label": doc.get("verdict", {}).get("label"),
                    "confidence": doc.get("verdict", {}).get("confidence"),
                    "risk_score": doc.get("risk_score"),
                    "language": doc.get("language"),
                    "satire_flag": False,
                    "mutation_of": doc.get("parent_claim_id"),
                    "predicted_6h_reach": doc.get("predicted_6h_reach", 0),
                    "reasoning_chain": doc.get("verdict", {}).get("reasoning_chain", []),
                    "evidence_sources": doc.get("verdict", {}).get("evidence_sources", []),
                    "processed_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                },
                error=None
            )
        else:
            return AnalyzeResponse(
                success=False,
                data=None,
                error="Claim is currently being processed by another ML task. Please check back in a few seconds."
            )

    # Build initial AgentState
    initial_state = {
        "claim_id": claim_id,
        "original_text": body.text,
        "source_platform": body.platform,
        "media_urls": body.media_urls,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "language": body.language or "",
        "translated_text": None,
        "atomic_claims": [],
        "evidence": [],
        "mutation_depth": 0,
        "mutation_of": None,
        "satire_flag": False,
        "confidence": 0.0,
        "risk_score": 0.0,
        "predicted_6h_reach": 0,
        "verdict": None,
        "reasoning_chain": [],
    }

    try:
        # Import and run the LangGraph pipeline
        from agent.graph import graph
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"ML pipeline failed for claim {claim_id}: {e}")
        raise HTTPException(status_code=500, detail=f"ML pipeline error: {str(e)}")

    verdict = final_state.get("verdict")
    if not verdict:
        return AnalyzeResponse(success=False, data=None, error="ML pipeline returned no verdict.")

    # INJECTION POINT 1 - FEDERATED NETWORK
    import asyncio
    try:
        asyncio.create_task(
            fednet_adapter.publish_detection(
                claim_text_normalized=body.text,
                embedding=[],
                confidence=float(verdict.get("confidence", 0.0)),
                category=str(verdict.get("category", "other")),
                verdict_label=str(verdict.get("label", "UNVERIFIED"))
            )
        )
    except Exception as e:
        logger.warning(f"Error publishing to federated network: {e}")

    # Save the full claim document to MongoDB
    db = request.app.mongodb
    claim_doc = {
        "claim_id": claim_id,
        "original_text": body.text,
        "translated_text": final_state.get("translated_text"),
        "language": final_state.get("language", "en"),
        "source": {
            "platform": body.platform,
            "account_id": body.account_id,
            "post_url": body.post_url,
            "posted_at": datetime.now(timezone.utc),
        },
        "media": {"type": "text", "url": "", "ocr_text": None, "transcription": None, "deepfake_score": None},
        "embedding_ref": None,
        "parent_claim_id": final_state.get("mutation_of"),
        "mutation_depth": final_state.get("mutation_depth", 0),
        "verdict": {
            "label": verdict.get("label"),
            "confidence": verdict.get("confidence"),
            "reasoning_chain": verdict.get("reasoning_chain", []),
            "evidence_sources": verdict.get("evidence_sources", []),
        },
        "risk_score": verdict.get("risk_score", 0.0),
        "predicted_6h_reach": final_state.get("predicted_6h_reach", 0),
        "actual_reach": 0,
        "action": None,
        "verdict_expires_at": None,
        "category": None,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        await db.claims.insert_one(claim_doc)
        logger.info(f"Saved claim {claim_id} to MongoDB")
    except Exception as e:
        logger.error(f"Failed to save claim {claim_id} to MongoDB: {e}")

    # Return the verdict to the caller
    return AnalyzeResponse(
        success=True,
        data={
            "claim_id": claim_id,
            "label": verdict.get("label"),
            "confidence": verdict.get("confidence"),
            "risk_score": verdict.get("risk_score"),
            "language": verdict.get("language"),
            "satire_flag": verdict.get("satire_flag"),
            "mutation_of": verdict.get("mutation_of"),
            "predicted_6h_reach": final_state.get("predicted_6h_reach", 0),
            "reasoning_chain": verdict.get("reasoning_chain", []),
            "evidence_sources": verdict.get("evidence_sources", []),
            "processed_at": verdict.get("processed_at"),
        },
        error=None,
    )


@router.get("/claim/{claim_id}", response_model=AnalyzeResponse)
async def get_analyzed_claim(claim_id: str, request: Request):
    """Fetch a previously analyzed claim from MongoDB."""
    db = request.app.mongodb
    doc = await db.claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not doc:
        return AnalyzeResponse(success=False, data=None, error="Claim not found.")
    # Convert datetime fields to ISO strings for JSON serialization
    if doc.get("created_at"):
        doc["created_at"] = doc["created_at"].isoformat()
    if doc.get("source", {}).get("posted_at"):
        doc["source"]["posted_at"] = doc["source"]["posted_at"].isoformat()
    return AnalyzeResponse(success=True, data=doc, error=None)
