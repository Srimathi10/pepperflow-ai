"""Redis client for caching and queue management."""

import redis.asyncio as redis

from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> redis.Redis:
    return redis_client
