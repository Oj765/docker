import json
import logging
import asyncio
from aiokafka import AIOKafkaConsumer
from app.config import get_settings
from app.routers.claims import manager
from app.services.timescaledb_service import timescaledb_service

logger = logging.getLogger(__name__)
settings = get_settings()

class KafkaConsumerService:
    def __init__(self):
        self.consumer = None
        self.task = None

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            "raw_posts",
            "verdict_ready",
            "alert_trigger",
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id="backend_api_consumer",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None
        )
        await self.consumer.start()
        logger.info("Kafka consumer started listening to raw_posts, verdict_ready, alert_trigger.")
        self.task = asyncio.create_task(self.consume_messages())

    async def consume_messages(self):
        from app.services.webhook_service import webhook_service
        from app.models.alert import WebhookPayload
        from app.services.kafka_producer import kafka_producer
        try:
            async for msg in self.consumer:
                logger.info(
                    f"Received message from topic {msg.topic} "
                    f"partition {msg.partition} "
                    f"offset {msg.offset} "
                    f"timestamp {msg.timestamp}"
                )
                payload = msg.value

                if msg.topic == "raw_posts":
                    from app.multimodal.pipeline import process_media_urls
                    media_urls = payload.get("media_urls", [])
                    if media_urls:
                        extracted_texts = await process_media_urls(media_urls)
                        payload["extracted_media_text"] = extracted_texts
                    await kafka_producer.send_message("normalized_claims", payload)
                    logger.info(f"Published to normalized_claims: {payload.get('post_id')}")

                elif msg.topic == "verdict_ready":
                    await manager.broadcast(payload)
                    await timescaledb_service.insert_virality_metric(
                        claim_id=payload.get("claim_id"),
                        platform=payload.get("platform", "unknown"),
                        predicted_6h_reach=payload.get("predicted_6h_reach", 0),
                        actual_reach=payload.get("actual_reach", 0),
                        risk_score=payload.get("risk_score", 0.0)
                    )

                elif msg.topic == "alert_trigger":
                    alert = WebhookPayload(**payload)
                    await webhook_service.dispatch_alert(alert)

        except asyncio.CancelledError:
            logger.info("Kafka consumer loop cancelled.")
        except Exception as e:
            logger.error(f"Error in Kafka consumer: {str(e)}")

    async def stop(self):
        if self.task:
            self.task.cancel()
        if self.consumer:
            await self.consumer.stop()
            logger.info("Kafka consumer stopped.")

kafka_consumer = KafkaConsumerService()