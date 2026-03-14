import time
import json
import random
import uuid
import feedparser
from datetime import datetime
from kafka import KafkaProducer

TOPIC_NAME = 'claims_stream'

# Live RSS feeds from real fact-checking organizations
FACT_CHECK_FEEDS = [
    {
        "url": "https://www.politifact.com/rss/rulings/f/",
        "source": "PolitiFact",
        "platform": "twitter"
    },
    {
        "url": "https://www.politifact.com/rss/rulings/pants-fire/",
        "source": "PolitiFact",
        "platform": "facebook"
    },
    {
        "url": "https://www.snopes.com/feed/",
        "source": "Snopes",
        "platform": "reddit"
    },
    {
        "url": "https://www.factcheck.org/feed/",
        "source": "FactCheck.org",
        "platform": "youtube"
    },
    {
        "url": "https://fullfact.org/feed/",
        "source": "Full Fact",
        "platform": "telegram"
    }
]

import os

def get_kafka_producer():
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    try:
        producer = KafkaProducer(
            bootstrap_servers=[bootstrap],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print(f"Connected to Kafka at {bootstrap}.")
        return producer
    except Exception as e:
        print(f"Kafka connection failed: {e}")
        return None

def fetch_real_claims():
    """Fetch real misinformation claims from fact-checking RSS feeds."""
    all_claims = []
    for feed_info in FACT_CHECK_FEEDS:
        try:
            print(f"Fetching from {feed_info['source']}...")
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                if title and len(title) > 15:
                    all_claims.append({
                        "title": title,
                        "source": feed_info["source"],
                        "platform": feed_info["platform"],
                        "link": entry.get("link", ""),
                        "published": entry.get("published", "")
                    })
            print(f"  → {len(feed.entries)} claims from {feed_info['source']}")
        except Exception as e:
            print(f"  Failed to fetch {feed_info['source']}: {e}")

    print(f"\nTotal real claims loaded: {len(all_claims)}")
    return all_claims

def stream_data():
    producer = get_kafka_producer()
    if not producer:
        return

    print("Fetching real claims from fact-checking organizations...")
    claims = fetch_real_claims()

    if not claims:
        print("No claims fetched — check your internet connection.")
        return

    random.shuffle(claims)
    print(f"Streaming {len(claims)} real claims to Kafka topic: [{TOPIC_NAME}]\n")

    while True:
        random.shuffle(claims)
        for row in claims:
            # Raw claim — NO risk scores. Your ML model will compute those.
            message = {
                "id": f"claim_{uuid.uuid4().hex[:8]}",
                "platform": row["platform"],
                "claim": row["title"],
                "source_org": row["source"],
                "fact_check_url": row.get("link", ""),
                "published": row.get("published", ""),
                "timestamp": datetime.utcnow().isoformat() + "Z",
                # Placeholders — to be filled by your ML model
                "risk_score": None,
                "risk_level": "pending",
                "confidence": None,
                "estimated_impressions": None
            }

            try:
                producer.send(TOPIC_NAME, value=message)
                producer.flush()
                print(f"[{row['source']}] {row['title'][:80]}")
            except Exception as e:
                print(f"Kafka error: {e}")

            # Simulate live social media post frequency: 2–5 seconds between claims
            time.sleep(random.uniform(2, 5))

if __name__ == "__main__":
    stream_data()
