from abc import ABC, abstractmethod
from typing import Optional


class IRedisService(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis by key."""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, expiry: Optional[int] = None) -> None:
        """Set a value in Redis with an expiry time."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a key from Redis."""
        pass

    @abstractmethod
    async def cache_jira_token(self, user_id: int, access_token: str, expiry: int = 3600) -> None:
        """Cache Jira access token with expiry."""
        pass

    @abstractmethod
    async def get_cached_jira_token(self, user_id: int) -> str:
        """Get Jira access token from cache if exists."""
        pass

    @abstractmethod
    async def cache_microsoft_token(self, user_id: int, access_token: str, expiry: int = 3600) -> None:
        """Cache microsoft access token with expiry."""
        pass

    @abstractmethod
    async def get_cached_microsoft_token(self, user_id: int) -> str:
        """Get microsoft access token from cache if exists."""
        pass
