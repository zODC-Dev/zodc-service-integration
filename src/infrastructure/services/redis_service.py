from typing import Any, Optional

from redis.asyncio import Redis

from src.configs.logger import log
from src.domain.services.redis_service import IRedisService


class RedisService(IRedisService):
    """Service for managing Redis operations."""

    def __init__(self, redis_client: "Redis[Any]"):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis by key."""
        value = await self.redis.get(key)
        if value:
            return value.decode('utf-8') if isinstance(value, bytes) else value
        return None

    async def set(self, key: str, value: str, expiry: Optional[int] = None) -> None:
        """Set a value in Redis with an expiry time."""
        if expiry is None:
            await self.redis.set(key, value)
        else:
            await self.redis.setex(key, expiry, value)

    async def delete(self, key: str) -> None:
        """Delete a key from Redis."""
        await self.redis.delete(key)

    async def cache_jira_token(self, user_id: int, access_token: str, expiry: int = 3600) -> None:
        """Cache Jira access token with expiry."""
        key = f"jira_token:{user_id}"
        await self.set(key, access_token, expiry)

    async def get_cached_jira_token(self, user_id: int) -> str:
        """Get Jira access token from cache if exists."""
        try:
            key = f"jira_token:{user_id}"
            token = await self.get(key)
            return token if token else ""
        except Exception as e:
            log.error(f"Error getting cached Jira token: {str(e)}")
            return ""

    async def cache_microsoft_token(self, user_id: int, access_token: str, expiry: int = 3600) -> None:
        """Cache Microsoft access token with expiry."""
        key = f"microsoft_token:{user_id}"
        await self.set(key, access_token, expiry)

    async def get_cached_microsoft_token(self, user_id: int) -> str:
        """Get Microsoft access token from cache if exists."""
        token = await self.get(f"microsoft_token:{user_id}")
        return token if token else ""
