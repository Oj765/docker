from fastapi import APIRouter
from app.models.alert import WebhookPayload
from app.services.webhook_service import webhook_service
from app.services.kafka_producer import kafka_producer

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.post("/test")
async def trigger_test_webhook(payload: WebhookPayload):
    # Send actual API alerts
    await webhook_service.dispatch_alert(payload)
    
    # Also log to high-severity kafka topic
    await kafka_producer.send_message("alert_trigger", payload.dict())

    return {
        "success": True,
        "data": "Webhook dispatched via Slack/Telegram and pushed to alert_trigger Kafka topic",
        "error": None
    }
