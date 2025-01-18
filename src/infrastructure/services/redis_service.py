import json
from typing import Any, Dict
from redis.asyncio import Redis

from src.domain.services.redis_service import IRedisService


class RedisService(IRedisService):
    """Service for managing Redis operations."""

    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def get(self, key: str) -> Any:
        """Get a value from Redis by key."""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Dict[str, Any], expiry: int) -> None:
        """Set a value in Redis with an expiry time."""
        await self.redis.setex(key, expiry, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        """Delete a key from Redis."""
        await self.redis.delete(key)

    async def cache_token(self, user_id: int, access_token: str, expiry: int) -> None:
        """Cache microsoft access token with expiry."""
        key = f"msft_token:{user_id}"
        token_data = {"access_token": access_token, "expiry": expiry}
        await self.set(key, token_data, expiry)

    async def get_cached_token(self, user_id: int) -> str:
        """Get microsoft access token from cache if exists and valid."""
        key = f"msft_token:{user_id}"
        token_data = await self.get(key)

        if token_data:
            # expiry = datetime.fromisoformat(cast(str, token_data["expiry"]))
            # if expiry > datetime.now():
            access_token: str = token_data.get("access_token", "")
            return access_token
        return ""

    async def cache_jira_token(self, user_id: int, access_token: str, expiry: int = 3600) -> None:
        """Cache Jira access token with expiry."""
        key = f"jira_token:{user_id}"
        token_data = {"access_token": access_token}
        await self.set(key, token_data, expiry)

    async def get_cached_jira_token(self, user_id: int) -> str:
        """Get Jira access token from cache if exists."""
        key = f"jira_token:{user_id}"
        token_data = await self.get(key)
        return token_data.get("access_token", "") if token_data else ""
