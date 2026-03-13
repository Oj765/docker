import json
from kafka import KafkaConsumer

TOPIC_NAME = 'claims_stream'

try:
    print(f"Connecting to Kafka at localhost:9092 for topic {TOPIC_NAME}...")
    consumer = KafkaConsumer(
        TOPIC_NAME,
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        consumer_timeout_ms=10000
    )
    print("Connected. Waiting for messages...")
    for message in consumer:
        print(f"Received: {message.value['id']}")
except Exception as e:
    print(f"Error: {e}")
