import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

class RedisDedupService:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        self.redis_client = redis.from_url(settings.redis_url, encoding="utf8", decode_responses=True)

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()

    async def is_duplicate(self, claim_id: str) -> bool:
        """
        Check if a claim_id already exists in the redis deduplication cache.
        If it doesn't, add it with a TTL of 30 minutes.
        """
        if not self.redis_client:
            return False

        cache_key = f"dedup:claim:{claim_id}"
        # Setnx returns 1 if key was set (meaning it was not a duplicate)
        # and 0 if key already exists (meaning it is a duplicate)
        is_new = await self.redis_client.setnx(cache_key, "1")
        if is_new == 1:
            # 30 minutes TTL
            await self.redis_client.expire(cache_key, 1800)
            return False
        return True

redis_dedup = RedisDedupService()
