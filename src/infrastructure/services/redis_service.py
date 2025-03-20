import json
from typing import Optional

from redis.asyncio import Redis

from src.configs.logger import log
from src.domain.services.redis_service import IRedisService


class RedisService(IRedisService):
    """Service for managing Redis operations."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis by key."""
        value = await self.redis.get(key)
        return value.decode('utf-8') if value else None

    async def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        """Set a value in Redis with an expiry time."""
        await self.redis.set(key, value.encode('utf-8'), ex=expire)

    async def delete(self, key: str) -> None:
        """Delete a key from Redis."""
        await self.redis.delete(key)

    async def cache_jira_token(self, user_id: int, access_token: str, expiry: int = 3600) -> None:
        """Cache Jira access token with expiry."""
        key = f"jira_token:{user_id}"
        token_data = {"access_token": access_token}
        await self.set(key, json.dumps(token_data, default=str), expiry)

    async def get_cached_jira_token(self, user_id: int) -> str:
        """Get Jira access token from cache if exists."""
        log.info(f"Getting cached Jira token for user {user_id}")
        key = f"jira_token:{user_id}"
        token_data = await self.get(key)
        return token_data.get("access_token", "") if token_data else ""

    async def cache_microsoft_token(self, user_id: int, access_token: str, expiry: int = 3600) -> None:
        """Cache Microsoft access token with expiry."""
        log.info(f"Caching Microsoft token for user {user_id}")
        key = f"microsoft_token:{user_id}"
        token_data = {"access_token": access_token}
        await self.set(key, json.dumps(token_data, default=str), expiry)

    async def get_cached_microsoft_token(self, user_id: int) -> str:
        """Get Microsoft access token from cache if exists."""
        key = f"microsoft_token:{user_id}"
        token_data = await self.get(key)
        return token_data.get("access_token", "") if token_data else ""
