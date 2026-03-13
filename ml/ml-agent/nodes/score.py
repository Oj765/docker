import logging
from typing import Dict, Any

from agent.state import AgentState
from models.amplification.features import build_amplification_features
from models.amplification.predict import get_reach_prediction

logger = logging.getLogger(__name__)


def _severity_from_risk(risk_score: float) -> str:
    if risk_score >= 0.85:
        return "CRITICAL"
    if risk_score >= 0.6:
        return "HIGH"
    return "LOW"

async def score_node(state: AgentState) -> Dict[str, Any]:
    evidence = state.get("evidence", [])
    reasoning = list(state.get("reasoning_chain", []))

    predicted_reach = int(state.get("predicted_6h_reach", 0) or 0)
    if predicted_reach <= 0:
        features = build_amplification_features(state)
        predicted_reach = get_reach_prediction(features)

    conf = 0.0
    if evidence:
        total_cred = sum(e.get("credibility_score", 0.5) for e in evidence)
        avg_cred = total_cred / len(evidence)
        source_weight = min(len(evidence) / 5.0, 1.0)

        conf = avg_cred * source_weight
        conf = max(conf, 0.2)

    conf = min(max(conf, 0.0), 1.0)

    mutation_depth = state.get("mutation_depth", 0)
    base_risk = min(predicted_reach / 15000.0, 0.55)
    mutation_risk = min(mutation_depth * 0.1, 0.3)

    risk_score = base_risk + mutation_risk

    text = state.get("original_text", "").lower()
    severe_keywords = ["cure", "vaccine", "virus", "election", "fraud", "scam", "riot", "bleach", "hoax"]
    if any(k in text for k in severe_keywords):
        risk_score += 0.2

    official_hits = sum(1 for e in evidence if e.get("source_type") == "official")
    high_cred_hits = sum(1 for e in evidence if e.get("credibility_score", 0.0) >= 0.85)
    if official_hits >= 1 and high_cred_hits >= 2:
        conf = min(conf + 0.1, 1.0)

    risk_score = min(max(risk_score, 0.0), 1.0)
    should_respond = conf >= 0.7 and risk_score >= 0.6
    review_required = True
    severity_rating = _severity_from_risk(risk_score)

    logger.info(f"Computed Confidence: {conf:.2f}, Risk Score: {risk_score:.2f}")

    reasoning.append(
        f"Score: Estimated 6h reach at {predicted_reach} and set confidence to {conf:.2f} from {len(evidence)} evidence source(s)."
    )
    reasoning.append(
        f"Score: Assigned {severity_rating} severity with risk score {risk_score:.2f}; auto-response recommendation={'yes' if should_respond else 'no'}."
    )

    return {
        "confidence": conf,
        "risk_score": risk_score,
        "predicted_6h_reach": predicted_reach,
        "should_respond": should_respond,
        "review_required": review_required,
        "reasoning_chain": reasoning
    }
