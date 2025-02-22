from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from aiohttp import ClientSession

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.refresh_tokens import TokenType
from src.domain.entities.refresh_token import RefreshTokenEntity
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.repositories.user_repository import IUserRepository
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_refresh_service import ITokenRefreshService


class TokenRefreshService(ITokenRefreshService):
    def __init__(
        self,
        redis_service: IRedisService,
        user_repository: IUserRepository,
        refresh_token_repository: IRefreshTokenRepository
    ):
        self.redis_service = redis_service
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

    async def refresh_microsoft_token(self, user_id: int) -> Optional[str]:
        """Refresh Microsoft access token"""
        try:
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
                await self._update_microsoft_tokens(user_id, data)
                return data.get("access_token")

        except Exception as e:
            log.error(f"Error refreshing Microsoft token: {str(e)}")
            return None

    async def refresh_jira_token(self, user_id: int) -> Optional[str]:
        """Refresh Jira access token"""
        try:
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
                        "refresh_token": refresh_token.token
                    }
                )
                data: Dict[str, str] = await response.json()

                if "error" in data:
                    log.error(f"Jira token refresh failed: {data}")
                    return None

                # Update tokens
                await self._update_jira_tokens(user_id, data)
                return data.get("access_token")

        except Exception as e:
            log.error(f"Error refreshing Jira token: {str(e)}")
            return None

    async def schedule_token_refresh(self, user_id: int) -> None:
        """Schedule token refresh for a user"""
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            return

        now = datetime.now(timezone.utc)
        refresh_threshold = timedelta(minutes=5)

        # Check Microsoft token
        microsoft_token = await self.refresh_token_repository.get_by_user_id_and_type(
            user_id=user_id,
            token_type=TokenType.MICROSOFT
        )
        if microsoft_token and microsoft_token.expires_at - now <= refresh_threshold:
            await self.refresh_microsoft_token(user_id)

        # Check Jira token
        jira_token = await self.refresh_token_repository.get_by_user_id_and_type(
            user_id=user_id,
            token_type=TokenType.JIRA
        )
        if jira_token and jira_token.expires_at - now <= refresh_threshold:
            await self.refresh_jira_token(user_id)

    async def _update_microsoft_tokens(self, user_id: int, token_data: Dict[str, Any]) -> None:
        """Update Microsoft tokens in database and cache"""
        # Store refresh token in refresh_tokens table
        if "refresh_token" in token_data:
            refresh_token = RefreshTokenEntity(
                token=token_data["refresh_token"],
                user_id=user_id,
                token_type=TokenType.MICROSOFT,
                expires_at=(datetime.now() + timedelta(days=30)).astimezone(timezone.utc)  # Adjust expiry as needed
            )
            await self.refresh_token_repository.create_refresh_token(refresh_token)

        # Cache access token
        await self.redis_service.cache_token(
            user_id=user_id,
            access_token=token_data["access_token"],
            expiry=token_data["expires_in"],
            token_type=TokenType.MICROSOFT
        )

    async def _update_jira_tokens(self, user_id: int, token_data: Dict[str, Any]) -> None:
        """Update Jira tokens in database and cache"""
        # Store refresh token in refresh_tokens table
        if "refresh_token" in token_data:
            refresh_token = RefreshTokenEntity(
                token=token_data["refresh_token"],
                user_id=user_id,
                token_type=TokenType.JIRA,
                expires_at=(datetime.now() + timedelta(days=30)).astimezone(timezone.utc)  # Adjust expiry as needed
            )
            await self.refresh_token_repository.create_refresh_token(refresh_token)

        # Cache access token
        await self.redis_service.cache_token(
            user_id=user_id,
            access_token=token_data["access_token"],
            expiry=token_data["expires_in"],
            token_type=TokenType.JIRA
        )
