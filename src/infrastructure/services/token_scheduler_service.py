from datetime import datetime, timedelta, timezone

from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.constants.refresh_tokens import TokenType
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.services.token_refresh_service import ITokenRefreshService
from src.domain.services.token_scheduler_service import ITokenSchedulerService


class TokenSchedulerService(ITokenSchedulerService):
    def __init__(
        self,
        token_refresh_service: ITokenRefreshService,
        refresh_token_repository: IRefreshTokenRepository
    ):
        self.token_refresh_service = token_refresh_service
        self.refresh_token_repository = refresh_token_repository
        self.refresh_threshold = timedelta(minutes=5)
        self.refresh_token_threshold = timedelta(days=7)

    async def schedule_token_refresh(self, session: AsyncSession, user_id: int) -> None:
        """Schedule token refresh check for a user"""
        try:
            log.info(f"Scheduling token refresh for user {user_id}")
            now = datetime.now(timezone.utc)

            # Check Jira tokens
            jira_token = await self.refresh_token_repository.get_by_user_id_and_type(
                session=session,
                user_id=user_id,
                token_type=TokenType.JIRA
            )
            if jira_token:
                if jira_token.expires_at - now <= self.refresh_threshold:
                    await self.refresh_token_chain(session, user_id, TokenType.JIRA)
                elif not jira_token.is_revoked and jira_token.expires_at - now <= self.refresh_token_threshold:
                    await self.rotate_refresh_token(session, user_id, TokenType.JIRA)

            # Check Microsoft tokens
            microsoft_token = await self.refresh_token_repository.get_by_user_id_and_type(
                session=session,
                user_id=user_id,
                token_type=TokenType.MICROSOFT
            )
            if microsoft_token:
                if microsoft_token.expires_at - now <= self.refresh_threshold:
                    await self.refresh_token_chain(session, user_id, TokenType.MICROSOFT)
                elif not microsoft_token.is_revoked and microsoft_token.expires_at - now <= self.refresh_token_threshold:
                    await self.rotate_refresh_token(session, user_id, TokenType.MICROSOFT)

        except Exception as e:
            log.error(f"Error in token refresh scheduler: {str(e)}")

    async def refresh_token_chain(self, session: AsyncSession, user_id: int, token_type: TokenType) -> None:
        """Refresh both access and refresh tokens"""
        try:
            if token_type == TokenType.JIRA:
                log.info(f"Refreshing Jira token for user {user_id}")
                new_access_token = await self.token_refresh_service.refresh_jira_token(session, user_id)
            else:
                new_access_token = await self.token_refresh_service.refresh_microsoft_token(session, user_id)

            if not new_access_token:
                log.error(f"Failed to refresh {token_type.value} token for user {user_id}")
                return

            log.info(f"Successfully refreshed {token_type.value} token for user {user_id}")

        except Exception as e:
            log.error(f"Error in refresh token chain: {str(e)}")

    async def rotate_refresh_token(self, session: AsyncSession, user_id: int, token_type: TokenType) -> None:
        """Rotate refresh token before it expires"""
        try:
            # Get current refresh token
            current_token = await self.refresh_token_repository.get_by_user_id_and_type(
                session=session,
                user_id=user_id,
                token_type=token_type
            )
            if not current_token or current_token.is_revoked:
                return

            # Refresh tokens which will create new refresh token
            await self.refresh_token_chain(session=session, user_id=user_id, token_type=token_type)

            # Revoke old refresh token
            await self.refresh_token_repository.revoke_token(session=session, token=current_token.token)
            log.info(f"Successfully rotated {token_type.value} refresh token for user {user_id}")

        except Exception as e:
            log.error(f"Error rotating refresh token: {str(e)}")
