"""
Node Registry
─────────────
Maintains the set of trusted peer nodes in the federated mesh.
Nodes self-register via HTTP POST. Registrations are persisted in MongoDB
so the mesh survives service restarts.

Design decisions:
  - No central authority: each node keeps its own registry copy.
  - Nodes that go silent for > STALE_THRESHOLD are marked inactive but not deleted.
  - Public keys are stored here; the crypto module caches derived key objects.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.signal import NodeRegistration, TrustScore
from ..core.config import FederatedNetworkSettings, get_base_trust_for_org

logger = logging.getLogger("federated_network.node_registry")

STALE_THRESHOLD_HOURS = 24


class NodeRegistry:
    def __init__(self, db: AsyncIOMotorDatabase, settings: FederatedNetworkSettings) -> None:
        self._nodes  = db[settings.MONGODB_NODE_COLLECTION]
        self._trusts = db[settings.MONGODB_TRUST_COLLECTION]
        self._settings = settings

    # ── Registration ───────────────────────────────────────────────────────────

    async def register_node(self, reg: NodeRegistration) -> bool:
        """
        Upsert a node registration. Returns True if new, False if updated.
        Always initialises a TrustScore if one doesn't exist yet.
        """
        now = datetime.now(timezone.utc)
        doc = reg.model_dump()
        doc["registered_at"] = now
        doc["last_seen"] = now
        doc["active"] = True

        result = await self._nodes.update_one(
            {"node_id": reg.node_id},
            {"$set": doc},
            upsert=True,
        )
        is_new = result.upserted_id is not None

        if is_new:
            base = get_base_trust_for_org(reg.org_type, self._settings)
            trust = TrustScore(
                node_id=reg.node_id,
                base_trust=base,
                accuracy_history=1.0,
                volume_penalty=0.0,
            )
            await self._trusts.update_one(
                {"node_id": reg.node_id},
                {"$setOnInsert": trust.model_dump()},
                upsert=True,
            )
            logger.info(
                "New node registered: %s (%s) base_trust=%.2f",
                reg.node_id, reg.org_type, base,
            )
        else:
            logger.debug("Node refreshed: %s", reg.node_id)

        return is_new

    async def heartbeat(self, node_id: str) -> None:
        """Called when we successfully receive from or reach a peer."""
        await self._nodes.update_one(
            {"node_id": node_id},
            {"$set": {"last_seen": datetime.now(timezone.utc), "active": True}},
        )

    # ── Lookup ─────────────────────────────────────────────────────────────────

    async def get_node(self, node_id: str) -> Optional[NodeRegistration]:
        doc = await self._nodes.find_one({"node_id": node_id})
        if not doc:
            return None
        doc.pop("_id", None)
        return NodeRegistration(**doc)

    async def get_active_peers(self) -> list[NodeRegistration]:
        """Returns all nodes that have been seen recently, excluding self."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=STALE_THRESHOLD_HOURS)
        cursor = self._nodes.find(
            {
                "node_id": {"$ne": self._settings.NODE_ID},
                "last_seen": {"$gte": cutoff},
                "active": True,
            }
        )
        nodes = []
        async for doc in cursor:
            doc.pop("_id", None)
            try:
                nodes.append(NodeRegistration(**doc))
            except Exception as exc:
                logger.warning("Malformed node doc skipped: %s", exc)
        return nodes

    async def get_all_nodes(self) -> list[NodeRegistration]:
        cursor = self._nodes.find({"node_id": {"$ne": self._settings.NODE_ID}})
        nodes = []
        async for doc in cursor:
            doc.pop("_id", None)
            try:
                nodes.append(NodeRegistration(**doc))
            except Exception as exc:
                logger.warning("Malformed node doc skipped: %s", exc)
        return nodes

    async def deactivate_node(self, node_id: str) -> None:
        await self._nodes.update_one(
            {"node_id": node_id},
            {"$set": {"active": False}},
        )
        logger.warning("Node deactivated: %s", node_id)

    async def node_count(self) -> int:
        return await self._nodes.count_documents({"active": True})
