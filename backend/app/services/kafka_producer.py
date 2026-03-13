import json
import logging
from aiokafka import AIOKafkaProducer
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class KafkaProducerService:
    def __init__(self):
        self.producer = None

    async def start(self):
        # Using aiokafka, connected to bootstrap servers
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        await self.producer.start()
        logger.info("Kafka producer started.")

    async def stop(self):
        if self.producer:
            await self.producer.stop()
            logger.info("Kafka producer stopped.")

    async def send_message(self, topic: str, message: dict):
        if not self.producer:
            raise Exception("Producer is not initialized.")
        try:
            # Send the message
            record_metadata = await self.producer.send_and_wait(topic, value=message)
            # Log every Kafka message with timestamp + topic + partition offset as requested
            logger.info(
                f"Sent message to topic {record_metadata.topic} "
                f"partition {record_metadata.partition} "
                f"offset {record_metadata.offset} "
                f"timestamp {record_metadata.timestamp}"
            )
        except Exception as e:
            logger.error(f"Failed to send Kafka message to {topic}: {str(e)}")

kafka_producer = KafkaProducerService()
