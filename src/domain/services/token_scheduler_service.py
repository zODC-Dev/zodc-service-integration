from abc import ABC, abstractmethod

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.constants.refresh_tokens import TokenType


class ITokenSchedulerService(ABC):
    @abstractmethod
    async def schedule_token_refresh(self, session: AsyncSession, user_id: int) -> None:
        """Schedule token refresh check for a user"""
        pass

    @abstractmethod
    async def refresh_token_chain(self, session: AsyncSession, user_id: int, token_type: TokenType) -> None:
        """Refresh both access and refresh tokens"""
        pass
