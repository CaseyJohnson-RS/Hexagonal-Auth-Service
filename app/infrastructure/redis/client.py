import redis.asyncio as aioredis

from app.config.settings import settings


def make_redis_client() -> aioredis.Redis:
    """Create an async Redis client from application settings."""
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
