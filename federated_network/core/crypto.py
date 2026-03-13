"""
Ed25519 signing and verification for federated signals.

Every signal published by this node is signed with its Ed25519 private key.
Every signal received from a peer is verified against the peer's registered public key.
This prevents signal forgery and man-in-the-middle injection.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from ..models.signal import FederatedSignal

logger = logging.getLogger("federated_network.crypto")


class SigningService:
    """
    Handles Ed25519 key loading, signal signing, and signature verification.
    Keys are loaded once at startup from PEM files (or Kubernetes secrets).
    """

    def __init__(self, private_key_path: str, public_key_path: str) -> None:
        self._private_key: Optional[Ed25519PrivateKey] = None
        self._public_key:  Optional[Ed25519PublicKey]  = None
        self._peer_keys:   dict[str, Ed25519PublicKey] = {}

        self._load_own_keys(private_key_path, public_key_path)

    def _load_own_keys(self, priv_path: str, pub_path: str) -> None:
        try:
            priv_pem = Path(priv_path).read_bytes()
            self._private_key = serialization.load_pem_private_key(priv_pem, password=None)
            logger.info("Ed25519 private key loaded from %s", priv_path)
        except FileNotFoundError:
            logger.warning(
                "Private key not found at %s — signal signing disabled. "
                "Generate with: openssl genpkey -algorithm ed25519 -out %s",
                priv_path, priv_path,
            )

        try:
            pub_pem = Path(pub_path).read_bytes()
            self._public_key = serialization.load_pem_public_key(pub_pem)
            logger.info("Ed25519 public key loaded from %s", pub_path)
        except FileNotFoundError:
            logger.warning("Public key not found at %s", pub_path)

    def sign_signal(self, signal: FederatedSignal) -> str:
        """
        Return base64-encoded Ed25519 signature over the signal's canonical payload.
        Raises RuntimeError if private key is not loaded (misconfigured node).
        """
        if self._private_key is None:
            raise RuntimeError(
                "Cannot sign signal — Ed25519 private key not loaded. "
                "Check FEDNET_ED25519_PRIVATE_KEY_PATH."
            )
        payload_bytes = signal.canonical_payload().encode("utf-8")
        raw_sig = self._private_key.sign(payload_bytes)
        return base64.b64encode(raw_sig).decode("ascii")

    def verify_signal(self, signal: FederatedSignal, peer_public_key_pem: str) -> bool:
        """
        Verify a signal's signature against the peer's registered public key.
        Returns False (not raises) on invalid signature so callers can decide policy.
        """
        if not signal.signature:
            logger.warning("Signal %s has no signature — rejecting", signal.signal_id)
            return False

        try:
            peer_key = self._get_or_cache_peer_key(signal.source_node, peer_public_key_pem)
            raw_sig = base64.b64decode(signal.signature)
            payload_bytes = signal.canonical_payload().encode("utf-8")
            peer_key.verify(raw_sig, payload_bytes)
            return True
        except InvalidSignature:
            logger.warning(
                "Invalid signature on signal %s from node %s",
                signal.signal_id, signal.source_node,
            )
            return False
        except Exception as exc:
            logger.error("Signature verification error for signal %s: %s", signal.signal_id, exc)
            return False

    def _get_or_cache_peer_key(self, node_id: str, pem: str) -> Ed25519PublicKey:
        if node_id not in self._peer_keys:
            key = serialization.load_pem_public_key(pem.encode("utf-8"))
            self._peer_keys[node_id] = key
        return self._peer_keys[node_id]

    def public_key_pem(self) -> str:
        """Export this node's public key as PEM string for registration."""
        if self._public_key is None:
            raise RuntimeError("Public key not loaded")
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def invalidate_peer_cache(self, node_id: str) -> None:
        """Call when a node's key rotates."""
        self._peer_keys.pop(node_id, None)
