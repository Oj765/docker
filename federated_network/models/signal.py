"""
Canonical federated signal data models.
All cross-node communication uses these schemas — no raw data ever leaves a node.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class SignalType(str, Enum):
    """Classification of what a federated signal represents."""
    CLAIM_DETECTED      = "claim_detected"       # New harmful claim identified
    CAMPAIGN_ALERT      = "campaign_alert"        # Coordinated campaign detected
    SOURCE_COMPROMISED  = "source_compromised"    # Source credibility collapsed
    NARRATIVE_SHIFT     = "narrative_shift"       # Narrative changing direction
    EARLY_WARNING       = "early_warning"         # Pre-viral detection signal
    RETRACTION          = "retraction"            # Previous signal was wrong


class TopicDomain(str, Enum):
    HEALTH      = "health"
    POLITICS    = "politics"
    SCIENCE     = "science"
    FINANCE     = "finance"
    MILITARY    = "military"
    ELECTION    = "election"
    CLIMATE     = "climate"
    OTHER       = "other"


class FederatedSignal(BaseModel):
    """
    The canonical privacy-preserving signal exchanged between federated nodes.

    Privacy contract:
      - claim_hash:     SHA-256 of normalized claim text — no raw text
      - embedding_hash: SHA-256 of claim embedding vector — no raw vector
      - No usernames, account IDs, post URLs, or personal identifiers allowed
    """
    signal_id:      str         = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_hash:     str         = Field(..., description="SHA-256 of normalized claim text")
    embedding_hash: str         = Field(..., description="SHA-256 of claim embedding bytes")
    signal_type:    SignalType
    confidence:     float       = Field(..., ge=0.0, le=1.0)
    topic_domain:   TopicDomain
    source_node:    str         = Field(..., description="Registered node ID of the publisher")
    trust_weight:   float       = Field(..., ge=0.0, le=1.0, description="Publisher's trust at emit time")
    timestamp:      datetime    = Field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds:    int         = Field(default=3600, ge=60, le=86400)
    signature:      Optional[str] = Field(None, description="Ed25519 hex signature over canonical payload")
    region_hint:    Optional[str] = Field(None, description="ISO 3166-1 alpha-2 region, e.g. 'US', 'IN'")
    mutation_depth: int         = Field(default=0, ge=0, description="How many hops from origin signal")
    consensus_peers: int        = Field(default=1, ge=1, description="Number of nodes that corroborated")

    @field_validator("claim_hash", "embedding_hash")
    @classmethod
    def must_be_sha256_hex(cls, v: str) -> str:
        if len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError("Hash fields must be 64-char lowercase hex (SHA-256)")
        return v.lower()

    @field_validator("source_node")
    @classmethod
    def node_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_node cannot be blank")
        return v.strip()

    def is_expired(self) -> bool:
        age = (datetime.now(timezone.utc) - self.timestamp).total_seconds()
        return age > self.ttl_seconds

    def canonical_payload(self) -> str:
        """Deterministic string used for signature verification."""
        return (
            f"{self.signal_id}|{self.claim_hash}|{self.embedding_hash}|"
            f"{self.signal_type}|{self.confidence}|{self.source_node}|"
            f"{self.timestamp.isoformat()}"
        )

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class AggregatedThreatPrior(BaseModel):
    """
    Output of the signal aggregator — feeds directly into the threat scoring engine.
    Represents a weighted consensus across all nodes that have seen this claim.
    """
    claim_hash:         str
    adjusted_confidence: float  = Field(..., ge=0.0, le=1.0)
    consensus_factor:   float   = Field(..., ge=0.0, le=1.0)
    contributing_nodes: int
    dominant_topic:     TopicDomain
    earliest_seen:      datetime
    signal_count:       int
    recommendation:     str     = Field(..., description="Suggested prior probability boost for local scorer")


class NodeRegistration(BaseModel):
    """A node's self-declaration when joining the federated mesh."""
    node_id:        str
    display_name:   str
    org_type:       str         = Field(..., description="e.g. WHO, NGO, GOV, RESEARCH, MEDIA")
    public_key_pem: str         = Field(..., description="Ed25519 public key for signature verification")
    endpoint_url:   str         = Field(..., description="HTTPS URL where this node receives signals")
    region:         Optional[str] = None
    capabilities:   list[str]   = Field(default_factory=list, description="e.g. ['health', 'multilingual']")
    registered_at:  datetime    = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen:      Optional[datetime] = None


class TrustScore(BaseModel):
    """Live trust record for a peer node."""
    node_id:            str
    base_trust:         float   = Field(..., ge=0.0, le=1.0)
    accuracy_history:   float   = Field(default=1.0, ge=0.0, le=1.0, description="Fraction of signals later validated")
    volume_penalty:     float   = Field(default=0.0, ge=0.0, le=0.5, description="Penalty for spam-like volume")
    effective_trust:    float   = Field(default=0.9, ge=0.0, le=1.0)
    last_updated:       datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_signals_sent: int     = Field(default=0)
    validated_correct:  int     = Field(default=0)

    @model_validator(mode="after")
    def compute_effective_trust(self) -> "TrustScore":
        self.effective_trust = round(
            self.base_trust * self.accuracy_history * (1.0 - self.volume_penalty),
            4,
        )
        return self


# ── Helpers ────────────────────────────────────────────────────────────────────

def hash_claim_text(normalized_text: str) -> str:
    """Deterministically hash claim text for privacy-safe sharing."""
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()


def hash_embedding(embedding: list[float]) -> str:
    """Hash a float embedding vector without exposing the raw vector."""
    raw = b"".join(f"{v:.6f}".encode() for v in embedding)
    return hashlib.sha256(raw).hexdigest()
