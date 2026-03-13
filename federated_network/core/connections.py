"""
Shared async connection pools for Redis and Kafka.
Single-instance pattern — imported by all federated_network sub-modules.
Do not create connections elsewhere; use these pools.
"""

from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer

from .config import FederatedNetworkSettings

logger = logging.getLogger("federated_network.connections")

_redis_pool:    Optional[aioredis.Redis]       = None
_kafka_producer: Optional[AIOKafkaProducer]    = None


async def get_redis(settings: FederatedNetworkSettings) -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("Redis pool initialized → %s", settings.REDIS_URL)
    return _redis_pool


async def get_kafka_producer(settings: FederatedNetworkSettings) -> AIOKafkaProducer:
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: v.encode("utf-8"),
            compression_type="gzip",
            acks="all",                    # durability over throughput
            enable_idempotence=True,
        )
        await _kafka_producer.start()
        logger.info("Kafka producer started → %s", settings.KAFKA_BOOTSTRAP_SERVERS)
    return _kafka_producer


async def close_connections() -> None:
    global _redis_pool, _kafka_producer
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("Redis pool closed")
    if _kafka_producer:
        await _kafka_producer.stop()
        _kafka_producer = None
        logger.info("Kafka producer stopped")
