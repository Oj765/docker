from fastapi import APIRouter, Request, Depends
from datetime import datetime
from app.models.verdict import ActionRequest
from app.services.kafka_producer import kafka_producer
from app.services.auth import require_role

router = APIRouter(prefix="/actions", tags=["actions"])

@router.post("/")
async def submit_action(
    action_request: ActionRequest, 
    request: Request,
    user: dict = Depends(require_role(["reviewer", "operator", "admin"]))
):
    db = request.app.mongodb
    
    action_data = {
        "type": action_request.action_type,
        "response_text": action_request.response_text,
        "posted_at": datetime.utcnow(),
        "reviewer_id": user["user_id"]
    }

    # Update claim in MongoDB
    result = await db.claims.update_one(
        {"claim_id": action_request.claim_id},
        {"$set": {"action": action_data}}
    )
    
    if result.matched_count == 0:
        return {"success": False, "data": None, "error": "Claim not found"}

    # Produce to action_log Kafka topic
    event_payload = {
        "claim_id": action_request.claim_id,
        "action": action_data
    }
    
    # Needs string representation for json
    eventPayload_serializable = {
        "claim_id": action_request.claim_id,
        "action": {
            "type": action_request.action_type,
            "response_text": action_request.response_text,
            "posted_at": action_data["posted_at"].isoformat(),
            "reviewer_id": user["user_id"]
        }
    }
    await kafka_producer.send_message("action_log", eventPayload_serializable)

    return {"success": True, "data": "Action applied and logged to Kafka", "error": None}
