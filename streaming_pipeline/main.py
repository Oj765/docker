import asyncio
import threading
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import kafka_consumer

app = FastAPI(title="Misinfo Live Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_websockets: list[WebSocket] = []
broadcaster_loop = None


def broadcast_sync(message: dict):
    """Callback triggered by the Kafka consumer thread to send data to websockets."""
    if broadcaster_loop and broadcaster_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_to_clients(message), broadcaster_loop)


async def broadcast_to_clients(message: dict):
    """Send the message to all connected WebSocket clients."""
    disconnected = []
    for connection in active_websockets:
        try:
            await connection.send_json(message)
        except Exception as e:
            print(f"Error sending to client: {e}")
            disconnected.append(connection)

    for conn in disconnected:
        if conn in active_websockets:
            active_websockets.remove(conn)


@app.on_event("startup")
async def startup_event():
    global broadcaster_loop
    broadcaster_loop = asyncio.get_running_loop()

    # Start Kafka Consumer in a background thread
    consumer_thread = threading.Thread(
        target=kafka_consumer.start_kafka_consumer,
        args=(broadcast_sync,),
        daemon=True
    )
    consumer_thread.start()
    print("Kafka Consumer thread started.")


@app.websocket("/ws/live-claims")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    print(f"WebSocket client connected. Total: {len(active_websockets)}")

    # Send any already-buffered claims immediately on connect
    cached = kafka_consumer.get_latest_claims()
    for claim in reversed(cached):
        try:
            await websocket.send_json(claim)
        except Exception:
            break

    try:
        # Keep alive: just wait for disconnect; a ping/pong or any frame closes cleanly
        while True:
            try:
                # Non-blocking wait with a timeout so we can detect disconnects
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                # Send a lightweight ping to verify client is still there
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break
    except WebSocketDisconnect:
        print("WebSocket client disconnected.")
    finally:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
        print(f"Clients remaining: {len(active_websockets)}")


@app.get("/claims")
async def get_claims():
    """Returns the latest 50 streamed claims."""
    return {"claims": kafka_consumer.get_latest_claims()}


@app.get("/claims/{claim_id}")
async def get_claim(claim_id: str):
    """Returns details of a specific claim."""
    claim = kafka_consumer.get_claim_by_id(claim_id)
    if claim:
        return claim
    raise HTTPException(status_code=404, detail="Claim not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
