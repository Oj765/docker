# backend/app/services/deepfake_db.py
# Run once at startup — adds indexes for deepfake queries.
# Call: await deepfake_db.setup()  inside FastAPI lifespan

async def setup(db):

    # Fast filter: "show me all deepfake-flagged claims"
    await db.claims.create_index([("media.deepfake_flagged", 1)])

    # Compound: flagged + risk score for threat prioritisation
    await db.claims.create_index([
        ("media.deepfake_flagged", 1),
        ("verdict.risk_score", -1),
    ])

    # Compound: platform + flagged (for per-platform dashboards)
    await db.claims.create_index([
        ("source.platform", 1),
        ("media.deepfake_flagged", 1),
    ])

    print("[deepfake_db] Indexes created")


async def get_flagged_claims(db, limit: int = 50, skip: int = 0) -> list[dict]:
    """Convenience query used by the dashboard deepfake feed."""
    cursor = (
        db.claims
        .find(
            {"media.deepfake_flagged": True},
            {
                "claim_id": 1, "original_text": 1,
                "source": 1, "verdict": 1,
                "media.deepfake_score": 1,
                "media.deepfake_model": 1,
                "media.url": 1,
                "media.type": 1,
                "created_at": 1,
            }
        )
        .sort("verdict.risk_score", -1)
        .skip(skip)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    return docs
