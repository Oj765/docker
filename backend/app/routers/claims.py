from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/claims", tags=["claims"])

# Dictionary to hold connected clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()


@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"msg": "alive"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from /claims/live")


# ── Live Claims stream WebSocket (/ws/live-claims) ──────────────────────────
live_router = APIRouter(tags=["live-stream"])

@live_router.websocket("/ws/live-claims")
async def live_claims_ws(websocket: WebSocket):
    """Streams raw messages from the claims_stream Kafka topic to the frontend."""
    await websocket.accept()
    consumer = AIOKafkaConsumer(
        "claims_stream",
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=None,  # no group — each connection gets its own offset (broadcast)
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None
    )
    try:
        await consumer.start()
        logger.info("Live-claims WebSocket consumer started.")
        ping_task = asyncio.create_task(_ping_loop(websocket))
        async for msg in consumer:
            if msg.value:
                try:
                    await websocket.send_json(msg.value)
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.warning(f"WS send error: {e}")
                    break
    except WebSocketDisconnect:
        logger.info("Live-claims client disconnected.")
    except Exception as e:
        logger.error(f"Live-claims WS error: {e}")
    finally:
        ping_task.cancel()
        await consumer.stop()


async def _ping_loop(ws: WebSocket):
    """Keep WS alive by sending a ping every 15 seconds."""
    try:
        while True:
            await asyncio.sleep(15)
            await ws.send_json({"type": "ping"})
    except Exception:
        pass


@router.get("/{claim_id}")
async def get_claim(claim_id: str, request: Request):
    db = request.app.mongodb
    if db is None:
         return {"success": False, "data": None, "error": "Database not initialized"}
    
    claim = await db.claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        return {"success": False, "data": None, "error": "Claim not found"}
    
    return {"success": True, "data": claim, "error": None}
