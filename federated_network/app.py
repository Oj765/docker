"""
Federated Network — FastAPI Application
────────────────────────────────────────
All HTTP endpoints for the federated detection mesh.

Endpoints:
  POST /fednet/v1/signals/receive     — receive signal from peer node
  POST /fednet/v1/nodes/register      — register or refresh a node
  GET  /fednet/v1/nodes               — list all known nodes
  GET  /fednet/v1/nodes/{node_id}     — get specific node info
  GET  /fednet/v1/priors/{claim_hash} — query aggregated prior for a claim
  GET  /fednet/v1/health              — liveness + mesh status
  POST /fednet/v1/admin/trust/feedback — submit signal accuracy feedback (admin)
  POST /fednet/v1/admin/nodes/{node_id}/deactivate — deactivate rogue node (admin)

Mounted as a sub-application: app.mount("/", fednet_app) in main platform's app.py
Or run standalone on a separate port for fully independent deployment.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Request, status
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

from .models.signal import FederatedSignal, NodeRegistration
from .core.config import FederatedNetworkSettings, get_settings
from .core.connections import get_redis, get_kafka_producer, close_connections
from .core.crypto import SigningService
from .node_registry.registry import NodeRegistry
from .trust_manager.manager import TrustManager
from .publisher.publisher import SignalPublisher
from .receiver.receiver import SignalReceiver
from .signal_aggregator.aggregator import SignalAggregator
from .prior_updater.updater import PriorUpdater, HttpThreatScorerAdapter

logger = logging.getLogger("federated_network.app")


# ── Dependency container ───────────────────────────────────────────────────────

class FedNetContainer:
    """Holds all instantiated services. Injected via FastAPI dependency."""
    settings:         FederatedNetworkSettings
    node_registry:    NodeRegistry
    trust_manager:    TrustManager
    signing_service:  SigningService
    publisher:        SignalPublisher
    receiver:         SignalReceiver
    aggregator:       SignalAggregator
    prior_updater:    PriorUpdater


_container: Optional[FedNetContainer] = None


def get_container() -> FedNetContainer:
    if _container is None:
        raise RuntimeError("FedNetContainer not initialised — app not started")
    return _container


# ── App lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _container

    settings = get_settings()
    logger.info("FederatedNetwork starting — node_id=%s", settings.NODE_ID)

    mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
    db           = mongo_client[settings.MONGODB_DB]
    redis        = await get_redis(settings)
    kafka        = await get_kafka_producer(settings)

    signing  = SigningService(settings.ED25519_PRIVATE_KEY_PATH, settings.ED25519_PUBLIC_KEY_PATH)
    registry = NodeRegistry(db, settings)
    trust    = TrustManager(db, settings)

    publisher = SignalPublisher(settings, signing, registry)
    receiver  = SignalReceiver(db, redis, settings, signing, registry, trust)
    aggregator = SignalAggregator(redis, kafka, trust, settings)

    scorer_adapter = HttpThreatScorerAdapter(
        base_url=settings.NODE_PUBLIC_URL,
        api_key=settings.NODE_ID,          # replaced by proper secret in production
    )
    prior_updater = PriorUpdater(settings, scorer_adapter)

    c = FedNetContainer()
    c.settings       = settings
    c.node_registry  = registry
    c.trust_manager  = trust
    c.signing_service = signing
    c.publisher      = publisher
    c.receiver       = receiver
    c.aggregator     = aggregator
    c.prior_updater  = prior_updater

    _container = c

    await aggregator.start()
    await prior_updater.start()

    logger.info("FederatedNetwork ready")
    yield

    # ── Shutdown ───────────────────────────────────────────────────────────────
    await aggregator.stop()
    await prior_updater.stop()
    await publisher.close()
    await close_connections()
    mongo_client.close()
    logger.info("FederatedNetwork shut down cleanly")


# ── Application ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="MisInfo Shield — Federated Network",
    version="1.0.0",
    description="Privacy-preserving federated threat intelligence mesh",
    lifespan=lifespan,
)


# ── Auth helpers ───────────────────────────────────────────────────────────────

async def require_node_header(
    x_fednet_node: str = Header(..., alias="X-Fednet-Node"),
    container:     FedNetContainer = Depends(get_container),
) -> str:
    """Verify the calling node is registered. Returns node_id."""
    node = await container.node_registry.get_node(x_fednet_node)
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Node '{x_fednet_node}' is not registered in this mesh",
        )
    return x_fednet_node


async def require_admin(request: Request) -> None:
    """Placeholder — integrate with platform's existing JWT/RBAC middleware."""
    # In production: validate JWT from Authorization header and check admin role
    # using Supabase Auth / Auth0 as per the platform tech stack.
    pass


# ── Signal endpoints ───────────────────────────────────────────────────────────

@app.post("/fednet/v1/signals/receive", status_code=202)
async def receive_signal(
    signal:    FederatedSignal,
    node_id:   str            = Depends(require_node_header),
    container: FedNetContainer = Depends(get_container),
):
    """
    Receive a federated signal from a peer node.
    Validates, deduplicates, and enqueues for async aggregation.
    Returns 202 Accepted immediately; processing is async.
    """
    result = await container.receiver.receive(signal)
    if not result.accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"signal_id": result.signal_id, "reason": result.reject_reason},
        )
    return {"signal_id": result.signal_id, "status": "accepted"}


# ── Node registry endpoints ────────────────────────────────────────────────────

@app.post("/fednet/v1/nodes/register", status_code=201)
async def register_node(
    registration: NodeRegistration,
    container:    FedNetContainer = Depends(get_container),
):
    """Register or refresh a node in this mesh instance."""
    is_new = await container.node_registry.register_node(registration)
    return {
        "node_id": registration.node_id,
        "status": "registered" if is_new else "refreshed",
        "mesh_node_count": await container.node_registry.node_count(),
    }


@app.get("/fednet/v1/nodes")
async def list_nodes(container: FedNetContainer = Depends(get_container)):
    nodes = await container.node_registry.get_all_nodes()
    return {
        "nodes": [
            {
                "node_id":      n.node_id,
                "display_name": n.display_name,
                "org_type":     n.org_type,
                "region":       n.region,
                "last_seen":    n.last_seen,
                "capabilities": n.capabilities,
            }
            for n in nodes
        ],
        "total": len(nodes),
    }


@app.get("/fednet/v1/nodes/{node_id}")
async def get_node(
    node_id:   str,
    container: FedNetContainer = Depends(get_container),
):
    node = await container.node_registry.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    trust = await container.trust_manager.get_trust(node_id)
    return {
        "node":  node.model_dump(exclude={"public_key_pem"}),  # never expose keys in API
        "trust": trust.model_dump() if trust else None,
    }


# ── Prior lookup ───────────────────────────────────────────────────────────────

@app.get("/fednet/v1/priors/{claim_hash}")
async def get_prior(
    claim_hash: str,
    container:  FedNetContainer = Depends(get_container),
):
    """
    Query the current aggregated federated prior for a claim hash.
    Used by the local threat scoring engine to boost risk scores.
    """
    prior = await container.aggregator.get_current_prior(claim_hash)
    if not prior:
        return JSONResponse(status_code=404, content={"detail": "No federated prior found"})
    return prior.model_dump()


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/fednet/v1/health")
async def health(container: FedNetContainer = Depends(get_container)):
    node_count = await container.node_registry.node_count()
    return {
        "status":     "ok",
        "node_id":    container.settings.NODE_ID,
        "org_type":   container.settings.ORG_TYPE,
        "mesh_nodes": node_count,
    }


# ── Admin endpoints ────────────────────────────────────────────────────────────

class TrustFeedbackPayload(BaseModel):
    node_id:     str
    signal_id:   str
    was_correct: bool


@app.post("/fednet/v1/admin/trust/feedback", dependencies=[Depends(require_admin)])
async def submit_trust_feedback(
    payload:   TrustFeedbackPayload,
    container: FedNetContainer = Depends(get_container),
):
    """
    Submit accuracy feedback for a signal. Updates the source node's trust score.
    Called by the platform's verdict-closed event handler.
    """
    await container.trust_manager.record_signal_validated(
        payload.node_id, payload.was_correct
    )
    trust = await container.trust_manager.get_trust(payload.node_id)
    return {
        "node_id":        payload.node_id,
        "effective_trust": trust.effective_trust if trust else None,
    }


@app.post(
    "/fednet/v1/admin/nodes/{node_id}/deactivate",
    dependencies=[Depends(require_admin)],
    status_code=204,
)
async def deactivate_node(
    node_id:   str,
    container: FedNetContainer = Depends(get_container),
):
    """Deactivate a node that is sending bad signals (admin action)."""
    await container.node_registry.deactivate_node(node_id)


# ── Error handlers ─────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error — federated network"},
    )
