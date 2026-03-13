# backend/app/main.py  (DIFF — add these lines to your existing main.py)

# ── Add to imports ────────────────────────────────────────────────────────────
from app.routers.geo import router as geo_router
from app.services import geo_db

# ── Add inside your existing @asynccontextmanager lifespan ───────────────────
# Find your existing lifespan function and add this line inside the startup block:
#
#   await geo_db.setup()
#
# Example (merge into your existing lifespan):
#
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # ... your existing startup code (Kafka, MongoDB, Redis) ...
#     await geo_db.setup()          # <-- ADD THIS
#     yield
#     # ... your existing shutdown code ...

# ── Add after your existing router includes ───────────────────────────────────
# app.include_router(geo_router, prefix="/geo", tags=["geo"])
#
# Full router registration block for reference:
#
# app.include_router(claims_router,    prefix="/claims",    tags=["claims"])
# app.include_router(actions_router,   prefix="/claims",    tags=["actions"])
# app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
# app.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
# app.include_router(audit_router,     prefix="/audit-log", tags=["audit"])
# app.include_router(webhooks_router,  prefix="/webhooks",  tags=["webhooks"])
# app.include_router(geo_router,       prefix="/geo",       tags=["geo"])   # <-- ADD
