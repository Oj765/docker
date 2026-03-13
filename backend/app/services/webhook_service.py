import httpx
import logging
from app.config import get_settings
from app.models.alert import WebhookPayload

logger = logging.getLogger(__name__)
settings = get_settings()

class WebhookService:
    async def dispatch_slack(self, payload: WebhookPayload, client: httpx.AsyncClient):
        if not settings.slack_webhook_url:
            return
        slack_data = {
            "text": f"*{payload.severity.upper()} Alert*: {payload.alert_type}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{payload.severity.upper()} Alert*: {payload.alert_type}\n{payload.message}"
                    }
                }
            ]
        }
        try:
            response = await client.post(settings.slack_webhook_url, json=slack_data)
            response.raise_for_status()
            logger.info(f"Dispatched webhook to Slack for alert: {payload.alert_type}")
        except Exception as e:
            logger.error(f"Failed to dispatch to Slack: {e}")

    async def dispatch_telegram(self, payload: WebhookPayload, client: httpx.AsyncClient):
        if not settings.telegram_bot_token or not settings.telegram_chat_id:
            return
        telegram_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        telegram_data = {
            "chat_id": settings.telegram_chat_id,
            "text": f"[{payload.severity.upper()}] {payload.alert_type}\n{payload.message}",
            "parse_mode": "HTML"
        }
        try:
            response = await client.post(telegram_url, json=telegram_data)
            response.raise_for_status()
            logger.info(f"Dispatched webhook to Telegram for alert: {payload.alert_type}")
        except Exception as e:
            logger.error(f"Failed to dispatch to Telegram: {e}")

    async def dispatch_alert(self, payload: WebhookPayload):
        async with httpx.AsyncClient() as client:
            await self.dispatch_slack(payload, client)
            await self.dispatch_telegram(payload, client)

webhook_service = WebhookService()
