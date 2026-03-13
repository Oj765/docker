# backend/app/services/geo_db.py
# Run once at startup to create geo indexes and TimescaleDB hypertable
# Call: await geo_db.setup() inside FastAPI lifespan

import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg

MONGO_URI  = os.getenv("MONGO_URI", "mongodb://localhost:27017")
TS_DSN     = os.getenv("TIMESCALEDB_DSN", "postgresql://postgres:postgres@localhost:5432/misinfo")

_mongo_client = None
_ts_pool      = None


async def setup():
    global _mongo_client, _ts_pool
    _mongo_client = AsyncIOMotorClient(MONGO_URI)
    db = _mongo_client.misinfo

    # ── MongoDB: geo indexes on claims collection ────────────────────────────
    await db.claims.create_index([("geo_metadata.affected_regions", 1)])
    await db.claims.create_index([("geo_metadata.country_of_origin", 1)])
    await db.claims.create_index([("geo_metadata.political_alignment", 1)])
    await db.claims.create_index([("geo_metadata.conflict_zone_overlap", 1)])
    await db.claims.create_index([
        ("geo_metadata.affected_regions", 1),
        ("created_at", -1)
    ])

    # ── TimescaleDB: geo_events hypertable ───────────────────────────────────
    _ts_pool = await asyncpg.create_pool(TS_DSN, min_size=2, max_size=10)
    async with _ts_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS geo_events (
                time                    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                claim_id                TEXT NOT NULL,
                country_code            CHAR(2) NOT NULL,
                region_type             TEXT,          -- 'origin' | 'affected'
                political_alignment     TEXT,
                target_demographic      TEXT,
                risk_score              FLOAT,
                geo_risk_multiplier     FLOAT,
                conflict_overlap        BOOLEAN DEFAULT FALSE,
                election_proximity_days INT,           -- NULL if no election
                health_overlap          BOOLEAN DEFAULT FALSE,
                verdict_label           TEXT
            );
        """)
        # Create hypertable if not already
        try:
            await conn.execute(
                "SELECT create_hypertable('geo_events', 'time', if_not_exists => TRUE);"
            )
        except Exception:
            pass

        # Continuous aggregate: hourly risk by country
        await conn.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS geo_hourly_risk
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 hour', time) AS bucket,
                country_code,
                COUNT(*)                    AS claim_count,
                AVG(risk_score)             AS avg_risk,
                MAX(risk_score)             AS max_risk,
                SUM(CASE WHEN conflict_overlap THEN 1 ELSE 0 END) AS conflict_claims,
                SUM(CASE WHEN health_overlap   THEN 1 ELSE 0 END) AS health_claims
            FROM geo_events
            GROUP BY bucket, country_code
            WITH NO DATA;
        """)

        await conn.execute("""
            CREATE MATERIALIZED VIEW IF NOT EXISTS geo_daily_risk
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket('1 day', time)  AS bucket,
                country_code,
                political_alignment,
                COUNT(*)                    AS claim_count,
                AVG(risk_score)             AS avg_risk,
                AVG(geo_risk_multiplier)    AS avg_multiplier
            FROM geo_events
            GROUP BY bucket, country_code, political_alignment
            WITH NO DATA;
        """)

    print("[geo_db] Setup complete — indexes + hypertable ready")


async def insert_geo_event(claim_id: str, geo: dict, verdict: dict):
    """Call after geo_tagger runs. Writes one row per affected region."""
    if not _ts_pool:
        return
    affected = geo.get("affected_regions", [])
    origin   = geo.get("country_of_origin")
    entries  = [(c, "affected") for c in affected]
    if origin and origin not in affected:
        entries.append((origin, "origin"))

    election_days = None
    prox = geo.get("election_proximity", [])
    if prox:
        election_days = min(e.get("days_away", 999) for e in prox)

    async with _ts_pool.acquire() as conn:
        for country_code, region_type in entries:
            await conn.execute("""
                INSERT INTO geo_events (
                    claim_id, country_code, region_type,
                    political_alignment, target_demographic,
                    risk_score, geo_risk_multiplier,
                    conflict_overlap, election_proximity_days, health_overlap,
                    verdict_label
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            """,
                claim_id,
                country_code,
                region_type,
                geo.get("political_alignment"),
                geo.get("target_demographic"),
                verdict.get("risk_score", 0.0),
                geo.get("geo_risk_multiplier", 1.0),
                geo.get("conflict_zone_overlap", False),
                election_days,
                geo.get("health_emergency_overlap", False),
                verdict.get("label"),
            )


async def get_heatmap_data(hours: int = 24) -> list[dict]:
    """Returns per-country risk aggregates for the world heatmap."""
    if not _ts_pool:
        return []
    async with _ts_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                country_code,
                SUM(claim_count)       AS total_claims,
                AVG(avg_risk)          AS avg_risk,
                MAX(max_risk)          AS max_risk,
                SUM(conflict_claims)   AS conflict_claims,
                SUM(health_claims)     AS health_claims
            FROM geo_hourly_risk
            WHERE bucket >= NOW() - INTERVAL '1 hour' * $1
            GROUP BY country_code
            ORDER BY avg_risk DESC;
        """, hours)
        return [dict(r) for r in rows]


async def get_timeline(country_code: str, days: int = 7) -> list[dict]:
    """Returns daily risk timeline for a specific country."""
    if not _ts_pool:
        return []
    async with _ts_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT bucket, claim_count, avg_risk, avg_multiplier
            FROM geo_daily_risk
            WHERE country_code = $1
              AND bucket >= NOW() - INTERVAL '1 day' * $2
            ORDER BY bucket ASC;
        """, country_code.upper(), days)
        return [dict(r) for r in rows]


async def get_alignment_breakdown(country_code: str) -> list[dict]:
    """Returns political alignment distribution for a country."""
    if not _ts_pool:
        return []
    async with _ts_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                political_alignment,
                COUNT(*)      AS count,
                AVG(risk_score) AS avg_risk
            FROM geo_events
            WHERE country_code = $1
              AND time >= NOW() - INTERVAL '30 days'
            GROUP BY political_alignment
            ORDER BY count DESC;
        """, country_code.upper())
        return [dict(r) for r in rows]
