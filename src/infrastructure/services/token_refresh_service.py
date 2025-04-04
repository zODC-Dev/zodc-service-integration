from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from aiohttp import ClientSession

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.refresh_tokens import TokenType
from src.domain.models.database.refresh_token import RefreshTokenDBCreateDTO
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_refresh_service import ITokenRefreshService
from src.utils.jwt_utils import get_jwt_expiry


class TokenRefreshService(ITokenRefreshService):
    def __init__(
        self,
        redis_service: IRedisService,
        user_repository: IJiraUserRepository,
        refresh_token_repository: IRefreshTokenRepository
    ):
        self.redis_service = redis_service
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

    async def refresh_microsoft_token(self, user_id: int) -> Optional[str]:
        """Refresh Microsoft access token"""
        try:
            log.info(f"Refreshing Microsoft token for user {user_id}")
            # Get refresh token from refresh_tokens table
            refresh_token = await self.refresh_token_repository.get_by_user_id_and_type(
                user_id=user_id,
                token_type=TokenType.MICROSOFT
            )
            if not refresh_token:
                return None

            # Exchange refresh token for new access token
            async with ClientSession() as session:
                response = await session.post(
                    "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                    data={
                        "client_id": settings.CLIENT_AZURE_CLIENT_ID,
                        "refresh_token": refresh_token.token,
                        "grant_type": "refresh_token",
                        "scope": "User.Read email profile offline_access openid"
                    }
                )
                data: Dict[str, str] = await response.json()

                if "error" in data:
                    log.error(f"Microsoft token refresh failed: {data}")
                    return None

                # Update tokens
                await self._save_new_microsoft_tokens(user_id, data)
                return data.get("access_token")

        except Exception as e:
            log.error(f"Error refreshing Microsoft token: {str(e)}")
            return None

    async def refresh_jira_token(self, user_id: int) -> Optional[str]:
        """Refresh Jira access token"""
        try:
            log.info(f"Refreshing Jira token for user {user_id}")
            # Get refresh token from refresh_tokens table
            refresh_token = await self.refresh_token_repository.get_by_user_id_and_type(
                user_id=user_id,
                token_type=TokenType.JIRA
            )
            if not refresh_token:
                return None

            # Exchange refresh token for new access token
            async with ClientSession() as session:
                response = await session.post(
                    "https://auth.atlassian.com/oauth/token",
                    data={
                        "grant_type": "refresh_token",
                        "client_id": settings.JIRA_CLIENT_ID,
                        "client_secret": settings.JIRA_CLIENT_SECRET,
                        "refresh_token": refresh_token.token,
                    }
                )
                data: Dict[str, str] = await response.json()

                if "error" in data:
                    log.error(f"Jira token refresh failed: {data}")
                    return None

                # Update tokens
                await self._save_new_jira_tokens(user_id, data)
                return data.get("access_token")

        except Exception as e:
            log.error(f"Error refreshing Jira token: {str(e)}")
            return None

    async def _save_new_microsoft_tokens(self, user_id: int, token_data: Dict[str, Any]) -> None:
        """Update Microsoft tokens in database and cache"""
        if "refresh_token" in token_data:
            refresh_token_expires_in = token_data.get("refresh_token_expires_in",
                                                      token_data.get("expires_in", 3600) * 2)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=refresh_token_expires_in)

            refresh_token_dto = RefreshTokenDBCreateDTO(
                token=token_data["refresh_token"],
                user_id=user_id,
                token_type=TokenType.MICROSOFT,
                expires_at=expires_at
            )
            await self.refresh_token_repository.create_refresh_token(refresh_token_dto)

        # Cache access token
        await self.redis_service.cache_microsoft_token(
            user_id=user_id,
            access_token=token_data["access_token"],
            expiry=token_data["expires_in"],
        )

    async def _save_new_jira_tokens(self, user_id: int, token_data: Dict[str, Any]) -> None:
        """Update Jira tokens in database and cache"""
        if "refresh_token" in token_data:
            # Try to get expiry from JWT for Jira
            expires_at = get_jwt_expiry(token_data["refresh_token"])
            if not expires_at:
                # Fallback to default if JWT decode fails
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600) * 2)

            refresh_token_dto = RefreshTokenDBCreateDTO(
                token=token_data["refresh_token"],
                user_id=user_id,
                token_type=TokenType.JIRA,
                expires_at=expires_at
            )
            await self.refresh_token_repository.create_refresh_token(refresh_token_dto)

        # Cache access token
        await self.redis_service.cache_jira_token(
            user_id=user_id,
            access_token=token_data["access_token"],
            expiry=token_data["expires_in"],
        )
