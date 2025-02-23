from abc import ABC, abstractmethod

from src.domain.constants.refresh_tokens import TokenType


class ITokenSchedulerService(ABC):
    @abstractmethod
    async def schedule_token_refresh(self, user_id: int) -> None:
        """Schedule token refresh check for a user"""
        pass

    @abstractmethod
    async def refresh_token_chain(self, user_id: int, token_type: TokenType) -> None:
        """Refresh both access and refresh tokens"""
        pass
