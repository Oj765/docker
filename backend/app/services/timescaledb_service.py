import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class TimescaleDBService:
    def __init__(self):
        self.pool = None

    def init(self, pool):
        self.pool = pool

    async def insert_virality_metric(
        self,
        claim_id: str,
        platform: str,
        predicted_6h_reach: int,
        actual_reach: int,
        risk_score: float
    ):
        if not self.pool:
            logger.warning("TimescaleDB pool not initialized, skipping insert.")
            return

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO virality_metrics 
                    (time, claim_id, platform, predicted_6h_reach, actual_reach, risk_score)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                datetime.now(timezone.utc),
                claim_id,
                platform,
                predicted_6h_reach,
                actual_reach,
                risk_score
            )
            logger.info(f"Inserted virality metric for claim_id={claim_id}")

timescaledb_service = TimescaleDBService()