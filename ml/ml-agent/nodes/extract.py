import logging
import spacy
from typing import Dict, Any

from agent.state import AgentState

logger = logging.getLogger(__name__)

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("en_core_web_sm not found. Run: python -m spacy download en_core_web_sm")
    nlp = None

async def extract_node(state: AgentState) -> Dict[str, Any]:
    text = state.get("translated_text") or state.get("original_text", "")
    logger.info(f"Extracting atomic claims from text length: {len(text)}")

    atomic_claims = []

    if nlp is not None and text.strip():
        doc = nlp(text)
        for sent in doc.sents:
            if len(sent.ents) > 0:
                atomic_claims.append(sent.text.strip())

    if not atomic_claims and text.strip():
        atomic_claims = [text.strip()]

    reasoning = list(state.get("reasoning_chain", []))
    reasoning.append(f"Extract: Reduced input into {len(atomic_claims)} checkable claim(s).")

    return {"atomic_claims": atomic_claims, "reasoning_chain": reasoning}
