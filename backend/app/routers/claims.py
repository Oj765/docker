from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
import asyncio
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/claims", tags=["claims"])

# Dictionary to hold connected clients
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()


@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Just keeping connection alive, server sends data proactively
            data = await websocket.receive_text()
            # Respond to ping or other inputs if needed
            await websocket.send_json({"msg": "alive"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from /claims/live")

@router.get("/{claim_id}")
async def get_claim(claim_id: str, request: Request):
    db = request.app.mongodb
    if db is None:
         return {"success": False, "data": None, "error": "Database not initialized"}
    
    # Motor returns dictionaries
    claim = await db.claims.find_one({"claim_id": claim_id}, {"_id": 0})
    if not claim:
        return {"success": False, "data": None, "error": "Claim not found"}
    
    return {"success": True, "data": claim, "error": None}
