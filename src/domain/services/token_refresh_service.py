from abc import ABC, abstractmethod
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession


class ITokenRefreshService(ABC):
    @abstractmethod
    async def refresh_microsoft_token(self, session: AsyncSession, user_id: int) -> Optional[str]:
        pass

    @abstractmethod
    async def refresh_jira_token(self, session: AsyncSession, user_id: int) -> Optional[str]:
        pass
