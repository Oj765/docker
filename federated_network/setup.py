#!/usr/bin/env python3
"""
setup.py — One-time setup for the Federated Network service.

Run this ONCE per node before first deployment:
    python -m services.federated_network.setup

Steps performed:
  1. Generate Ed25519 keypair → ./secrets/
  2. Create MongoDB indexes for performance + TTL
  3. Print the public key PEM for sharing with peer nodes
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


def generate_keys(secrets_dir: str = "./secrets") -> tuple[str, str]:
    """Generate Ed25519 keypair and write to PEM files."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    Path(secrets_dir).mkdir(parents=True, exist_ok=True)
    priv_path = f"{secrets_dir}/fednet_private_key.pem"
    pub_path  = f"{secrets_dir}/fednet_public_key.pem"

    if Path(priv_path).exists():
        print(f"⚠️  Private key already exists at {priv_path} — skipping generation")
        print("   Delete it manually if you need to rotate keys.")
        pub_pem = Path(pub_path).read_text()
        return priv_path, pub_pem

    private_key = Ed25519PrivateKey.generate()
    public_key  = private_key.public_key()

    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    Path(priv_path).write_bytes(priv_pem)
    Path(pub_path).write_bytes(pub_pem_bytes)

    # Secure the private key
    os.chmod(priv_path, 0o600)
    os.chmod(pub_path,  0o644)

    print(f"✅ Ed25519 keypair generated:")
    print(f"   Private: {priv_path} (mode 600 — keep secret)")
    print(f"   Public:  {pub_path}  (share with peer nodes)")

    return priv_path, pub_pem_bytes.decode()


async def create_mongodb_indexes(mongo_uri: str, db_name: str) -> None:
    """Create all required indexes for the federated network collections."""
    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo import ASCENDING, DESCENDING

    client = AsyncIOMotorClient(mongo_uri)
    db     = client[db_name]

    # ── federated_signals ──────────────────────────────────────────────────────
    signals = db["federated_signals"]
    await signals.create_index([("signal_id", ASCENDING)],     unique=True)
    await signals.create_index([("claim_hash", ASCENDING)])
    await signals.create_index([("source_node", ASCENDING)])
    await signals.create_index([("topic_domain", ASCENDING)])
    await signals.create_index([("timestamp", DESCENDING)])
    # TTL: auto-delete signals older than 7 days
    await signals.create_index(
        [("received_at", ASCENDING)],
        expireAfterSeconds=7 * 24 * 3600,
        name="signal_ttl_index",
    )
    print("✅ federated_signals indexes created")

    # ── federated_nodes ────────────────────────────────────────────────────────
    nodes = db["federated_nodes"]
    await nodes.create_index([("node_id", ASCENDING)], unique=True)
    await nodes.create_index([("org_type", ASCENDING)])
    await nodes.create_index([("last_seen", DESCENDING)])
    await nodes.create_index([("active", ASCENDING)])
    print("✅ federated_nodes indexes created")

    # ── federated_trust ────────────────────────────────────────────────────────
    trust = db["federated_trust"]
    await trust.create_index([("node_id", ASCENDING)], unique=True)
    await trust.create_index([("effective_trust", DESCENDING)])
    print("✅ federated_trust indexes created")

    client.close()


def create_kafka_topics(bootstrap_servers: str) -> None:
    """Create required Kafka topics if they don't exist."""
    try:
        from kafka.admin import KafkaAdminClient, NewTopic
        admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
        topics = [
            NewTopic(name="threat.prior.update", num_partitions=6, replication_factor=1),
        ]
        existing = admin.list_topics()
        to_create = [t for t in topics if t.name not in existing]
        if to_create:
            admin.create_topics(to_create)
            for t in to_create:
                print(f"✅ Kafka topic created: {t.name}")
        else:
            print("✅ Kafka topics already exist")
        admin.close()
    except ImportError:
        print("⚠️  kafka-python not installed — create topics manually:")
        print("   kafka-topics.sh --create --topic threat.prior.update "
              "--partitions 6 --replication-factor 1")
    except Exception as exc:
        print(f"⚠️  Kafka topic creation failed (may already exist): {exc}")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="FedNet one-time node setup")
    parser.add_argument("--secrets-dir",  default="./secrets")
    parser.add_argument("--mongo-uri",    default=os.getenv("FEDNET_MONGODB_URI", "mongodb://localhost:27017"))
    parser.add_argument("--mongo-db",     default=os.getenv("FEDNET_MONGODB_DB",  "misinfo_shield"))
    parser.add_argument("--kafka",        default=os.getenv("FEDNET_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    parser.add_argument("--keys-only",    action="store_true")
    args = parser.parse_args()

    print("\n── MisInfo Shield Federated Network Setup ─────────────────────────\n")

    _, pub_pem = generate_keys(args.secrets_dir)

    if not args.keys_only:
        asyncio.run(create_mongodb_indexes(args.mongo_uri, args.mongo_db))
        create_kafka_topics(args.kafka)

    print("\n── Your Public Key (share with peer nodes for registration) ────────\n")
    print(pub_pem)
    print("────────────────────────────────────────────────────────────────────\n")
    print("Setup complete. Start the service with:")
    print("  uvicorn services.federated_network.app:app --host 0.0.0.0 --port 8100\n")


if __name__ == "__main__":
    main()
