import asyncio
import json
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer

BOOTSTRAP_SERVERS = "localhost:9092"

MOCK_CLAIMS = [
    {
        "platform": "twitter",
        "post_id": "t-001",
        "text": "5G towers are causing COVID-19 symptoms in nearby residents",
        "author_id": "user_123",
        "author_followers": 45000,
        "media_urls": [],
        "engagement": {"likes": 1200, "shares": 890, "comments": 340},
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "platform": "reddit",
        "post_id": "r-001",
        "text": "New study shows vaccines contain microchips for tracking",
        "author_id": "user_456",
        "author_followers": 12000,
        "media_urls": [],
        "engagement": {"likes": 3400, "shares": 2100, "comments": 890},
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "platform": "telegram",
        "post_id": "tg-001",
        "text": "Government secretly adding fluoride to water to control population",
        "author_id": "channel_789",
        "author_followers": 89000,
        "media_urls": [],
        "engagement": {"likes": 5600, "shares": 4200, "comments": 1200},
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "platform": "twitter",
        "post_id": "t-002",
        "text": "Election machines were hacked in 12 states, votes changed",
        "author_id": "user_321",
        "author_followers": 230000,
        "media_urls": [],
        "engagement": {"likes": 8900, "shares": 7600, "comments": 3400},
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat()
    },
    {
        "platform": "reddit",
        "post_id": "r-002",
        "text": "WHO confirms bird flu has 60% human mortality rate, pandemic incoming",
        "author_id": "user_654",
        "author_followers": 67000,
        "media_urls": [],
        "engagement": {"likes": 12000, "shares": 9800, "comments": 4500},
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat()
    }
]

async def pump_claims():
    producer = AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )
    await producer.start()
    print("Mock ingestion started — pumping claims into raw_posts...")

    try:
        for claim in MOCK_CLAIMS:
            await producer.send("raw_posts", claim)
            print(f"Published: [{claim['platform']}] {claim['text'][:60]}...")
            await asyncio.sleep(3)  # 3s delay between claims for demo effect

        print("All mock claims published.")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(pump_claims())