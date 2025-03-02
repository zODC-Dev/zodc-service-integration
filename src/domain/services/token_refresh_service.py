from abc import ABC, abstractmethod
from typing import Optional


class ITokenRefreshService(ABC):
    @abstractmethod
    async def refresh_microsoft_token(self, user_id: int) -> Optional[str]:
        pass

    @abstractmethod
    async def refresh_jira_token(self, user_id: int) -> Optional[str]:
        pass
