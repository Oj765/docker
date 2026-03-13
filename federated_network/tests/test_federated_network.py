"""
Test suite for the Federated Network service.
Uses pytest-asyncio + AsyncMock. No real Redis/Mongo/Kafka needed for unit tests.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from ..models.signal import (
    FederatedSignal, SignalType, TopicDomain, TrustScore,
    hash_claim_text, hash_embedding,
)
from ..receiver.receiver import SignalReceiver, RejectReason
from ..trust_manager.manager import TrustManager
from ..signal_aggregator.aggregator import SignalAggregator


# ── Fixtures ───────────────────────────────────────────────────────────────────

def make_signal(**kwargs) -> FederatedSignal:
    defaults = dict(
        claim_hash=hash_claim_text("vaccines cause autism"),
        embedding_hash=hash_embedding([0.1, 0.2, 0.3]),
        signal_type=SignalType.CLAIM_DETECTED,
        confidence=0.85,
        topic_domain=TopicDomain.HEALTH,
        source_node="node-who-001",
        trust_weight=0.95,
        signature="a" * 88,  # placeholder base64
    )
    defaults.update(kwargs)
    return FederatedSignal(**defaults)


def make_settings(**kwargs):
    from ..core.config import FederatedNetworkSettings
    defaults = dict(
        NODE_ID="node-local-test",
        NODE_PUBLIC_URL="https://local.misinfo.example",
        ED25519_PRIVATE_KEY_PATH="/dev/null",
        ED25519_PUBLIC_KEY_PATH="/dev/null",
    )
    defaults.update(kwargs)
    with patch.dict("os.environ", {f"FEDNET_{k}": str(v) for k, v in defaults.items()}):
        return FederatedNetworkSettings(**defaults)


# ── Model tests ────────────────────────────────────────────────────────────────

class TestFederatedSignal:
    def test_valid_signal_constructs(self):
        sig = make_signal()
        assert sig.confidence == 0.85
        assert len(sig.claim_hash) == 64

    def test_invalid_confidence_rejected(self):
        with pytest.raises(Exception):
            make_signal(confidence=1.5)

    def test_invalid_hash_rejected(self):
        with pytest.raises(Exception):
            make_signal(claim_hash="not_a_valid_hash")

    def test_expired_signal_detected(self):
        old_ts = datetime.now(timezone.utc) - timedelta(seconds=7200)
        sig = make_signal(ttl_seconds=3600, timestamp=old_ts)
        assert sig.is_expired() is True

    def test_fresh_signal_not_expired(self):
        sig = make_signal(ttl_seconds=3600)
        assert sig.is_expired() is False

    def test_canonical_payload_deterministic(self):
        sig = make_signal()
        assert sig.canonical_payload() == sig.canonical_payload()

    def test_canonical_payload_contains_required_fields(self):
        sig = make_signal()
        payload = sig.canonical_payload()
        assert sig.signal_id  in payload
        assert sig.claim_hash in payload
        assert sig.source_node in payload


class TestHashing:
    def test_hash_claim_text_is_64_hex(self):
        h = hash_claim_text("some claim")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_text_same_hash(self):
        assert hash_claim_text("abc") == hash_claim_text("abc")

    def test_different_texts_different_hashes(self):
        assert hash_claim_text("claim A") != hash_claim_text("claim B")

    def test_hash_embedding_is_64_hex(self):
        h = hash_embedding([0.1, 0.2, 0.9])
        assert len(h) == 64

    def test_same_embedding_same_hash(self):
        emb = [0.1, 0.5, 0.9]
        assert hash_embedding(emb) == hash_embedding(emb)


class TestTrustScore:
    def test_effective_trust_computed_on_construction(self):
        t = TrustScore(node_id="n1", base_trust=0.9, accuracy_history=0.8, volume_penalty=0.1)
        expected = round(0.9 * 0.8 * 0.9, 4)
        assert t.effective_trust == expected

    def test_effective_trust_capped_at_1(self):
        t = TrustScore(node_id="n1", base_trust=1.0, accuracy_history=1.0, volume_penalty=0.0)
        assert t.effective_trust <= 1.0


# ── Receiver tests ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestSignalReceiver:
    def _make_receiver(self, node_exists=True, sig_valid=True):
        settings = make_settings()

        db_mock       = MagicMock()
        db_col_mock   = AsyncMock()
        db_col_mock.insert_one = AsyncMock()
        db_mock.__getitem__ = MagicMock(return_value=db_col_mock)

        redis_mock = AsyncMock()
        redis_mock.set  = AsyncMock(return_value=True)   # not replay by default
        redis_mock.incr = AsyncMock(return_value=1)
        redis_mock.expire = AsyncMock()
        redis_mock.xadd = AsyncMock()

        from ..models.signal import NodeRegistration
        node = NodeRegistration(
            node_id="node-who-001",
            display_name="WHO",
            org_type="WHO",
            public_key_pem="-----BEGIN PUBLIC KEY-----\nfake\n-----END PUBLIC KEY-----\n",
            endpoint_url="https://who.example.com",
        ) if node_exists else None

        registry_mock = AsyncMock()
        registry_mock.get_node       = AsyncMock(return_value=node)
        registry_mock.heartbeat      = AsyncMock()

        trust_mock = AsyncMock()
        trust_mock.get_signal_count_last_minute = AsyncMock(return_value=1)
        trust_mock.record_signal_received       = AsyncMock()

        signer_mock = MagicMock()
        signer_mock.verify_signal = MagicMock(return_value=sig_valid)

        receiver = SignalReceiver(
            db=db_mock, redis=redis_mock, settings=settings,
            signing_service=signer_mock, node_registry=registry_mock,
            trust_manager=trust_mock,
        )
        return receiver

    async def test_valid_signal_accepted(self):
        receiver = self._make_receiver()
        sig = make_signal()
        result = await receiver.receive(sig)
        assert result.accepted is True

    async def test_replay_rejected(self):
        receiver = self._make_receiver()
        receiver._redis.set = AsyncMock(return_value=None)  # None = key existed = replay
        sig = make_signal()
        result = await receiver.receive(sig)
        assert result.accepted is False
        assert result.reject_reason == RejectReason.REPLAY

    async def test_expired_signal_rejected(self):
        receiver = self._make_receiver()
        old_ts = datetime.now(timezone.utc) - timedelta(seconds=7200)
        sig = make_signal(ttl_seconds=3600, timestamp=old_ts)
        result = await receiver.receive(sig)
        assert result.accepted is False
        assert result.reject_reason == RejectReason.EXPIRED

    async def test_unknown_node_rejected(self):
        receiver = self._make_receiver(node_exists=False)
        sig = make_signal()
        result = await receiver.receive(sig)
        assert result.accepted is False
        assert result.reject_reason == RejectReason.UNKNOWN_NODE

    async def test_bad_signature_rejected(self):
        receiver = self._make_receiver(sig_valid=False)
        sig = make_signal()
        result = await receiver.receive(sig)
        assert result.accepted is False
        assert result.reject_reason == RejectReason.BAD_SIGNATURE

    async def test_rate_limited_rejected(self):
        receiver = self._make_receiver()
        receiver._trust.get_signal_count_last_minute = AsyncMock(return_value=9999)
        sig = make_signal()
        result = await receiver.receive(sig)
        assert result.accepted is False
        assert result.reject_reason == RejectReason.RATE_LIMITED


# ── Aggregator tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestSignalAggregator:
    def _make_aggregator(self):
        settings = make_settings()

        redis_mock = AsyncMock()
        redis_mock.setex = AsyncMock()
        redis_mock.get   = AsyncMock(return_value=None)

        kafka_mock = AsyncMock()
        kafka_mock.send = AsyncMock()

        trust_mock = AsyncMock()
        trust_mock.get_effective_trust = AsyncMock(return_value=0.9)

        return SignalAggregator(
            redis=redis_mock,
            kafka_producer=kafka_mock,
            trust_manager=trust_mock,
            settings=settings,
        )

    async def test_single_signal_produces_prior(self):
        agg = self._make_aggregator()
        signals = [make_signal()]
        await agg._aggregate_batch(signals)
        agg._kafka.send.assert_awaited_once()

    async def test_multi_node_consensus_boosts_confidence(self):
        agg = self._make_aggregator()
        claim = hash_claim_text("flu vaccine is dangerous")
        signals = [
            make_signal(claim_hash=claim, source_node="node-a", confidence=0.8),
            make_signal(claim_hash=claim, source_node="node-b", confidence=0.8),
            make_signal(claim_hash=claim, source_node="node-c", confidence=0.8),
        ]
        prior = await agg._compute_prior(claim, signals)
        assert prior is not None
        # 3 nodes → consensus_factor = 1.10 → adjusted > base confidence
        assert prior.adjusted_confidence > 0.8
        assert prior.contributing_nodes == 3

    async def test_recommendation_high_threat(self):
        agg = self._make_aggregator()
        rec = agg._build_recommendation(0.9, 3)
        assert "HIGH_THREAT" in rec

    async def test_recommendation_low(self):
        agg = self._make_aggregator()
        rec = agg._build_recommendation(0.3, 1)
        assert "LOW" in rec
