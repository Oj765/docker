import json
from kafka import KafkaConsumer

TOPIC_NAME = 'claims_stream'
MAX_CLAIMS = 50

# In-memory storage for the latest claims
latest_claims = []

def start_kafka_consumer(new_message_callback=None):
    """
    Start the Kafka consumer in a loop.
    new_message_callback is a function to call when a new message arrives.
    """
    try:
        print(f"Initializing Kafka Consumer for topic: {TOPIC_NAME}...")
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='earliest',  # Changed to earliest to populate initial data
            enable_auto_commit=True,
            group_id='misinfo-dashboard-group-v2', # New group to ensure we get all data
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        print(f"Successfully connected to Kafka. Listening for messages on {TOPIC_NAME}...")

        for message in consumer:
            claim_data = message.value
            
            # Store in memory, keep the latest MAX_CLAIMS
            latest_claims.insert(0, claim_data)
            if len(latest_claims) > MAX_CLAIMS:
                latest_claims.pop()
                
            print(f"Consumed claim: {claim_data['id']}")
            
            # Broadcast to WebSockets via callback
            if new_message_callback:
                new_message_callback(claim_data)
                
    except Exception as e:
        print(f"Consumer Error: {e}")

def get_latest_claims():
    return latest_claims

def get_claim_by_id(claim_id):
    for claim in latest_claims:
        if claim['id'] == claim_id:
            return claim
    return None
