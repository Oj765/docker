"""
Shared configuration and infrastructure for the federated network service.
All environment variables are namespaced under FEDNET_ to avoid collisions
with the rest of the MisInfo Shield platform.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger("federated_network")


class FederatedNetworkSettings(BaseSettings):
    # ── Node identity ──────────────────────────────────────────────────────────
    NODE_ID:            str = Field(..., description="Unique identifier for this node")
    NODE_DISPLAY_NAME:  str = Field(default="MisInfo Shield Node")
    ORG_TYPE:           str = Field(default="NGO", description="WHO | GOV | NGO | RESEARCH | MEDIA")
    NODE_REGION:        Optional[str] = Field(default=None)
    NODE_PUBLIC_URL:    str = Field(..., description="Public HTTPS base URL of this node")

    # ── Cryptographic signing ──────────────────────────────────────────────────
    ED25519_PRIVATE_KEY_PATH: str = Field(default="/run/secrets/fednet_private_key.pem")
    ED25519_PUBLIC_KEY_PATH:  str = Field(default="/run/secrets/fednet_public_key.pem")

    # ── Trust defaults (org_type → base_trust) ────────────────────────────────
    TRUST_WHO:      float = Field(default=0.95)
    TRUST_GOV:      float = Field(default=0.90)
    TRUST_RESEARCH: float = Field(default=0.85)
    TRUST_NGO:      float = Field(default=0.75)
    TRUST_MEDIA:    float = Field(default=0.65)
    TRUST_UNKNOWN:  float = Field(default=0.40)

    # ── Signal propagation ─────────────────────────────────────────────────────
    DEFAULT_SIGNAL_TTL_SECONDS: int  = Field(default=3600)
    MAX_MUTATION_DEPTH:         int  = Field(default=3,   description="Prevent signal echo storms")
    MIN_CONFIDENCE_TO_PUBLISH:  float = Field(default=0.6)
    REPLAY_WINDOW_SECONDS:      int  = Field(default=300, description="Window for replay-attack detection")

    # ── Redis (Kafka Streams used for main pipeline; Redis Streams for low-lat) ─
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_SIGNAL_STREAM:     str = Field(default="fednet:signals:inbound")
    REDIS_PROCESSED_STREAM:  str = Field(default="fednet:signals:processed")
    REDIS_CONSUMER_GROUP:    str = Field(default="fednet-aggregator")

    # ── Kafka (main platform bus) ──────────────────────────────────────────────
    KAFKA_BOOTSTRAP_SERVERS: str  = Field(default="localhost:9092")
    KAFKA_THREAT_PRIOR_TOPIC: str = Field(default="threat.prior.update")

    # ── MongoDB ────────────────────────────────────────────────────────────────
    MONGODB_URI:  str = Field(default="mongodb://localhost:27017")
    MONGODB_DB:   str = Field(default="misinfo_shield")
    MONGODB_SIGNAL_COLLECTION: str = Field(default="federated_signals")
    MONGODB_NODE_COLLECTION:   str = Field(default="federated_nodes")
    MONGODB_TRUST_COLLECTION:  str = Field(default="federated_trust")

    # ── HTTP federation ────────────────────────────────────────────────────────
    HTTP_PUBLISH_TIMEOUT_SECONDS: int  = Field(default=5)
    HTTP_MAX_RETRIES:             int  = Field(default=3)
    HTTP_BACKOFF_FACTOR:          float = Field(default=0.5)

    # ── Rate limiting ──────────────────────────────────────────────────────────
    MAX_SIGNALS_PER_NODE_PER_MINUTE: int = Field(default=100)

    class Config:
        env_prefix = "FEDNET_"
        env_file   = ".env"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> FederatedNetworkSettings:
    return FederatedNetworkSettings()


def get_base_trust_for_org(org_type: str, settings: FederatedNetworkSettings) -> float:
    """Map org_type string to configured base trust score."""
    mapping = {
        "WHO":      settings.TRUST_WHO,
        "GOV":      settings.TRUST_GOV,
        "RESEARCH": settings.TRUST_RESEARCH,
        "NGO":      settings.TRUST_NGO,
        "MEDIA":    settings.TRUST_MEDIA,
    }
    return mapping.get(org_type.upper(), settings.TRUST_UNKNOWN)
