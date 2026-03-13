import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, Field

from agent.state import AgentState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic schemas (used for prompt guidance; Groq returns raw JSON)
# ---------------------------------------------------------------------------
class EvidenceSourceSchema(BaseModel):
    url: str
    title: str
    credibility_score: float
    excerpt: str


class VerdictSchema(BaseModel):
    label: str = Field(description="'FALSE' | 'MISLEADING' | 'UNVERIFIED' | 'TRUE'")
    confidence: float = Field(description="float between 0.0 and 1.0")
    reasoning_chain: list[str] = Field(description="each step the agent took to verify")
    evidence_sources: list[EvidenceSourceSchema]
    satire_flag: bool


def _severity_from_risk(risk_score: float) -> str:
    if risk_score >= 0.85:
        return "CRITICAL"
    if risk_score >= 0.6:
        return "HIGH"
    return "LOW"


# ---------------------------------------------------------------------------
# LLM client setup — Groq first, Gemini as fallback
# ---------------------------------------------------------------------------
groq_client = None
gemini_client = None
LLM_PROVIDER = "none"

# Try Groq first (preferred)
if os.getenv("GROQ_API_KEY"):
    try:
        from groq import Groq
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        LLM_PROVIDER = "groq"
        logger.info("LLM provider: Groq (llama-3.3-70b-versatile)")
    except ImportError:
        logger.warning("groq package not installed. pip install groq")

# Fallback to Gemini
if not groq_client and os.getenv("GEMINI_API_KEY"):
    try:
        from google import genai
        from google.genai import types as genai_types
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        LLM_PROVIDER = "gemini"
        logger.info("LLM provider: Gemini 2.0 Flash")
    except ImportError:
        logger.warning("google-genai package not installed.")

# Load system prompt
try:
    with open(os.path.join(os.path.dirname(__file__), "..", "prompts", "verdict_system.txt"), "r", encoding="utf-8") as fh:
        SYSTEM_PROMPT = fh.read()
except Exception:
    SYSTEM_PROMPT = "You are a professional fact checker. Output structured JSON."

# JSON schema string for Groq prompt injection
VERDICT_JSON_SCHEMA = """{
  "label": "FALSE | MISLEADING | UNVERIFIED | TRUE",
  "confidence": 0.0,
  "reasoning_chain": ["step1", "step2", "step3"],
  "satire_flag": false
}"""


def _top_evidence(evidence: list, max_count: int = 5) -> list:
    """Return the top N evidence items sorted by credibility, ensuring 3-5 sources."""
    sorted_ev = sorted(evidence, key=lambda e: e.get("credibility_score", 0), reverse=True)
    return sorted_ev[:max(min(len(sorted_ev), max_count), 0)]


# ---------------------------------------------------------------------------
# Groq LLM call
# ---------------------------------------------------------------------------
async def _call_groq(user_prompt: str) -> dict:
    def _sync_call():
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2048,
        )
        return json.loads(response.choices[0].message.content)

    return await asyncio.to_thread(_sync_call)


# ---------------------------------------------------------------------------
# Gemini LLM call (fallback)
# ---------------------------------------------------------------------------
async def _call_gemini(user_prompt: str) -> dict:
    from google.genai import types as genai_types

    response = await asyncio.to_thread(
        gemini_client.models.generate_content,
        model="gemini-2.0-flash",
        contents=user_prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=VerdictSchema,
            temperature=0.1,
        ),
    )
    return json.loads(response.text)


# ---------------------------------------------------------------------------
# Main verdict node
# ---------------------------------------------------------------------------
async def verdict_node(state: AgentState) -> Dict[str, Any]:
    claim = state.get("translated_text") or state.get("original_text", "")
    evidence = list(state.get("evidence", []))
    reasoning = list(state.get("reasoning_chain", []))
    satire = state.get("satire_flag", False)
    computed_conf = float(state.get("confidence", 0.0) or 0.0)

    if satire:
        return {"verdict": _mock_verdict(state, evidence, reasoning + ["Flagged as satire shortcut."])}

    if LLM_PROVIDER == "none":
        logger.warning("No LLM API key found (GROQ_API_KEY or GEMINI_API_KEY). Returning fallback verdict.")
        return {"verdict": _mock_verdict(state, evidence, reasoning)}

    try:
        evidence_text = "\n\n".join(
            f"Source: {item.get('url')} (Credibility: {item.get('credibility_score', 0)})\n"
            f"Title: {item.get('title')}\n"
            f"Content: {item.get('excerpt')}"
            for item in evidence
        )
        user_prompt = (
            f"Claim to verify:\n{claim}\n\n"
            f"Gathered Evidence:\n{evidence_text if evidence else 'No evidence found.'}\n\n"
            f"Return ONLY valid JSON matching this schema:\n{VERDICT_JSON_SCHEMA}"
        )

        if LLM_PROVIDER == "groq":
            llm_output = await _call_groq(user_prompt)
            reasoning.append("Verdict: Used Groq (Llama 3.3 70B) for final evaluation.")
        else:
            llm_output = await _call_gemini(user_prompt)
            reasoning.append("Verdict: Used Gemini 2.0 Flash for final evaluation.")

        final_confidence = min(max((float(llm_output.get("confidence", 0.5)) + computed_conf) / 2.0, 0.0), 1.0)
        risk_score = float(state.get("risk_score", 0.5) or 0.5)
        severity_rating = _severity_from_risk(risk_score)
        formatted_reasoning = reasoning + ["LLM Evaluation:"] + list(llm_output.get("reasoning_chain", []))

        # Use PIPELINE evidence (3-5 sources), NOT LLM-generated sources
        top_sources = _top_evidence(evidence, max_count=5)

        verdict = {
            "claim_id": state.get("claim_id", "unknown"),
            "label": llm_output.get("label", "UNVERIFIED"),
            "confidence": final_confidence,
            "risk_score": risk_score,
            "reasoning_chain": formatted_reasoning,
            "evidence_sources": top_sources,
            "satire_flag": llm_output.get("satire_flag", False),
            "language": state.get("language", "en"),
            "mutation_of": state.get("mutation_of"),
            "predicted_6h_reach": int(state.get("predicted_6h_reach", 0) or 0),
            "severity_rating": severity_rating,
            "geo_info": state.get("geo_info", {}),
            "narrative": state.get("narrative", {}),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"verdict": verdict, "reasoning_chain": formatted_reasoning}
    except Exception as exc:
        logger.error("LLM generation failed: %s", exc)
        return {"verdict": _mock_verdict(state, evidence, reasoning)}


def _mock_verdict(state: AgentState, evidence: list[dict], reasoning: list[str]) -> Dict[str, Any]:
    risk_score = float(state.get("risk_score", 0.5) or 0.5)
    reasoning.append("Verdict fallback: LLM API skipped or failed. Using conservative fallback generation.")
    top_sources = _top_evidence(evidence, max_count=5)
    return {
        "claim_id": state.get("claim_id", "unknown"),
        "label": "UNVERIFIED",
        "confidence": float(state.get("confidence", 0.1) or 0.1),
        "risk_score": risk_score,
        "reasoning_chain": reasoning,
        "evidence_sources": top_sources,
        "satire_flag": state.get("satire_flag", False),
        "language": state.get("language", "en"),
        "mutation_of": state.get("mutation_of"),
        "predicted_6h_reach": int(state.get("predicted_6h_reach", 0) or 0),
        "severity_rating": _severity_from_risk(risk_score),
        "geo_info": state.get("geo_info", {}),
        "narrative": state.get("narrative", {}),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }
