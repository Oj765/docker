from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import asyncpg
from app.config import get_settings
from app.routers import claims, actions, analytics, campaigns, audit, webhooks, analyze, graph, geo
from app.services.kafka_producer import kafka_producer
from app.services.kafka_consumer import kafka_consumer
from app.services.redis_dedup import redis_dedup
from prometheus_fastapi_instrumentator import Instrumentator
from app.services.timescaledb_service import timescaledb_service
import sys
import os

try:
    from app.services import deepfake_db
except ImportError:
    deepfake_db = None

FEDNET_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if FEDNET_PATH not in sys.path:
    sys.path.insert(0, FEDNET_PATH)
try:
    from federated_network.app import app as fednet_app
except ImportError:
    fednet_app = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize MongoDB
    logger.info("Connecting to MongoDB...")
    app.mongodb_client = AsyncIOMotorClient(settings.mongo_uri, uuidRepresentation="standard")
    app.mongodb = app.mongodb_client[settings.mongo_db]
    logger.info("Connected to MongoDB.")
    # Startup: Initialize TimescaleDB
    logger.info("Connecting to TimescaleDB...")
    app.timescaledb_pool = await asyncpg.create_pool(settings.timescaledb_url)
    timescaledb_service.init(app.timescaledb_pool)
    # Run init script to create table + hypertable if not exists
    async with app.timescaledb_pool.acquire() as conn:
        with open("app/db/timescaledb_init.sql") as f:
            await conn.execute(f.read())
    logger.info("TimescaleDB connected and schema initialized.")
    timescaledb_service.init(app.timescaledb_pool)
    # Startup: Initialize Redis
    logger.info("Connecting to Redis...")
    await redis_dedup.connect()
    
    # Startup: Initialize Kafka
    logger.info("Starting Kafka services...")
    await kafka_producer.start()
    await kafka_consumer.start()

    if deepfake_db:
        logger.info("Initializing Deepfake DB...")
        await deepfake_db.setup()

    yield

    # Shutdown
    logger.info("Closing TimescaleDB pool...")
    await app.timescaledb_pool.close()
    logger.info("Shutting down... stopping Kafka services")
    await kafka_consumer.stop()
    await kafka_producer.stop()
    
    logger.info("Disconnecting from Redis...")
    await redis_dedup.disconnect()
    
    logger.info("Disconnecting from MongoDB...")
    app.mongodb_client.close()

app = FastAPI(title="Misinfo Shield API", lifespan=lifespan)

# Allow Vite dev (port 5173) and any localhost origin to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
# Include routers
app.include_router(claims.router)
app.include_router(actions.router)
app.include_router(analytics.router)
app.include_router(campaigns.router)
app.include_router(audit.router)
app.include_router(webhooks.router)
app.include_router(analyze.router)
app.include_router(graph.router)
app.include_router(geo.router, prefix="/geo", tags=["geo"])

try:
    from app.routers.deepfake import router as deepfake_internal_router
    from app.routers.deepfake_public import router as deepfake_public_router
    app.include_router(deepfake_internal_router, prefix="/internal/deepfake", tags=["deepfake-internal"])
    app.include_router(deepfake_public_router, prefix="/deepfake", tags=["deepfake"])
except ImportError as e:
    logger.warning(f"Could not load deepfake routers: {e}")

if fednet_app:
    app.mount("/fednet", fednet_app)

@app.get("/health")
async def health_check():
    return {"success": True, "data": "OK", "error": None}