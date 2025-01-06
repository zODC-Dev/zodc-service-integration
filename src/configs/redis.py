from __future__ import annotations

from typing import Optional

from redis.asyncio import Redis

from src.configs.settings import settings

_redis_client: Optional[Redis] = None


async def get_redis_client() -> Redis:
    """Get Redis client instance.

    Returns:
        Redis: Redis client instance
    """
    global _redis_client
    if _redis_client:
        return _redis_client
    else:
        _redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
        )
        return _redis_client
