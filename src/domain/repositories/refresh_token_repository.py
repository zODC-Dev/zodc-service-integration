from abc import ABC, abstractmethod
from typing import Optional

from src.domain.constants.refresh_tokens import TokenType
from src.domain.models.refresh_token import RefreshTokenModel


class IRefreshTokenRepository(ABC):
    @abstractmethod
    async def create_refresh_token(self, refresh_token: RefreshTokenModel) -> RefreshTokenModel:
        """Create new refresh token"""
        pass

    @abstractmethod
    async def get_by_token(self, token: str) -> Optional[RefreshTokenModel]:
        """Get refresh token by token string"""
        pass

    @abstractmethod
    async def revoke_token(self, token: str) -> None:
        """Revoke a refresh token"""
        pass

    @abstractmethod
    async def get_by_user_id_and_type(self, user_id: int, token_type: TokenType) -> Optional[RefreshTokenModel]:
        """Get refresh token by user id and token type"""
        pass

    @abstractmethod
    async def revoke_tokens_by_user_and_type(self, user_id: int, token_type: TokenType) -> None:
        """Revoke all tokens of a specific type for a user"""
        pass
