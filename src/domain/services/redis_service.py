from abc import ABC, abstractmethod
from typing import Any, Dict


class IRedisService(ABC):
    @abstractmethod
    async def get(self, key: str) -> Dict[str, Any]:
        """Get a value from Redis by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Dict[str, Any], expiry: int):
        """Set a value in Redis with an expiry time."""
        pass

    @abstractmethod
    async def delete(self, key: str):
        """Delete a key from Redis."""
        pass

    @abstractmethod
    async def cache_token(self, user_id: int, access_token: str, expiry: int):
        """Cache microsoft access token with expiry."""
        pass

    @abstractmethod
    async def get_cached_token(self, user_id: int) -> str:
        """Get microsoft access token from cache if exists and valid."""
        pass
