import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

from agent.state import AgentState

logger = logging.getLogger(__name__)

# Try Groq first
groq_client = None
gemini_client = None
LLM_PROVIDER = "none"

if os.getenv("GROQ_API_KEY"):
    try:
        from groq import Groq
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        LLM_PROVIDER = "groq"
    except ImportError:
        pass

if not groq_client and os.getenv("GEMINI_API_KEY"):
    try:
        from google import genai
        gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        LLM_PROVIDER = "gemini"
    except ImportError:
        pass

try:
    with open(os.path.join(os.path.dirname(__file__), "..", "prompts", "counter_narrative_system.txt"), "r", encoding="utf-8") as fh:
        SYSTEM_PROMPT = fh.read()
except Exception:
    SYSTEM_PROMPT = "You are the Counter-Narrative Engine."

async def _call_groq(user_prompt: str) -> dict:
    def _sync_call():
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=2048,
        )
        return json.loads(response.choices[0].message.content)
    return await asyncio.to_thread(_sync_call)

async def _call_gemini(user_prompt: str) -> dict:
    from google.genai import types as genai_types
    response = await asyncio.to_thread(
        gemini_client.models.generate_content,
        model="gemini-2.0-flash",
        contents=user_prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )
    return json.loads(response.text)

async def counter_narrative_node(state: AgentState) -> Dict[str, Any]:
    verdict = state.get("verdict")
    
    # We only generate countermeasures for FALSE or high-risk claims
    if not verdict or verdict.get("label") not in ["FALSE", "MISLEADING"]:
        return state
        
    if LLM_PROVIDER == "none":
        logger.warning("No LLM provider available for Counter Narrative Engine.")
        return state
        
    try:
        campaign_data = state.get("narrative", {})
        evidence_sources = verdict.get("evidence_sources", [])
        
        # Build prompt payload per instructions
        payload = {
            "claim_text": state.get("original_text", ""),
            "verdict": verdict.get("label"),
            "verdict_sources": [
                {
                    "title": src.get("title", ""),
                    "url": src.get("url", ""),
                    "credibility_score": src.get("credibility_score", 0.0)
                } for src in evidence_sources
            ],
            "campaign_data": {
                "times_seen_this_week": int(state.get("predicted_6h_reach", 0)),
                "coordinated_burst_detected": len(campaign_data.get("linked_claims", [])) > 5,
                "severity": verdict.get("severity_rating", "low").lower(),
                "platforms": [campaign_data.get("platform", "unknown")],
                "dominant_emotion": "fear", # fallback, real inference ideally comes from upstream
                "target_demographic": "General Public" 
            },
            "request_type": "generate"
        }

        user_prompt = f"Please generate counter-narratives for the following scenario based strictly on the JSON data provided below:\n{json.dumps(payload, indent=2)}"

        if LLM_PROVIDER == "groq":
            result = await _call_groq(user_prompt)
        else:
            result = await _call_gemini(user_prompt)

        state["counter_narrative"] = result
        state["reasoning_chain"].append("Counter-Narrative Engine: successfully generated intervention strategies.")
        
    except Exception as exc:
        logger.error("Counter-Narrative Engine failed: %s", exc)
        state["reasoning_chain"].append(f"Counter-Narrative Engine failed: {exc}")

    return state
