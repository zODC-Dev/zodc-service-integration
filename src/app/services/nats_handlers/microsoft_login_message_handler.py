from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from src.app.dtos.user.user_event_dto import MicrosoftLoginEventDTO
from src.configs.logger import log
from src.domain.constants.refresh_tokens import TokenType
from src.domain.models.jira_user import JiraUserCreateDTO
from src.domain.models.refresh_token import RefreshTokenModel
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.services.nats_message_handler import INATSMessageHandler
from src.domain.services.redis_service import IRedisService


class MicrosoftLoginMessageHandler(INATSMessageHandler):
    def __init__(
        self,
        redis_service: IRedisService,
        user_repository: IJiraUserRepository,
        refresh_token_repository: IRefreshTokenRepository
    ):
        self.redis_service = redis_service
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

    async def handle(self, subject: str, message: Dict[str, Any]) -> None:
        try:
            event = MicrosoftLoginEventDTO(**message)

            # Check if user exists
            user = await self.user_repository.get_user_by_email(event.email)
            if not user:
                new_user = JiraUserCreateDTO(
                    email=event.email,
                    user_id=event.user_id,
                )
                await self.user_repository.create_user(new_user)
                log.info(f"Created new user from Microsoft login for user {event.user_id}")

            # Store refresh token
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=event.expires_in * 2)
            refresh_token = RefreshTokenModel(
                token=event.refresh_token,
                user_id=event.user_id,
                token_type=TokenType.MICROSOFT,
                expires_at=expires_at
            )
            await self.refresh_token_repository.create_refresh_token(refresh_token)

            # Cache access token
            await self.redis_service.cache_microsoft_token(
                user_id=event.user_id,
                access_token=event.access_token,
                expiry=event.expires_in
            )

            log.info(f"Successfully processed Microsoft login for user {event.user_id}")
        except Exception as e:
            log.error(f"Error handling Microsoft login event: {str(e)}")


# class JiraLoginHandler(INATSMessageHandler):
#     def __init__(
#         self,
#         redis_service: IRedisService,
#         user_repository: IJiraUserRepository,
#         refresh_token_repository: IRefreshTokenRepository
#     ):
#         self.redis_service = redis_service
#         self.user_repository = user_repository
#         self.refresh_token_repository = refresh_token_repository

#     async def handle(self, subject: str, message: Dict[str, Any]) -> None:
#         try:
#             event = JiraLoginEventDTO(**message)

#             # Create or update user
#             user = await self.user_repository.get_user_by_email(event.email)
#             if not user:
#                 new_user = JiraUserCreateDTO(
#                     email=event.email,
#                     user_id=event.user_id,
#                     jira_account_id=event.account_id,
#                     jira_site_url=event.site_url
#                 )
#                 await self.user_repository.create_user(new_user)
#                 log.info(f"Created new user from Jira login for user {event.user_id}")
#             else:
#                 # Update existing user's Jira info
#                 await self.user_repository.update_user_jira_info(
#                     user.id,
#                     event.account_id,
#                     event.site_url
#                 )
#                 log.info(f"Updated Jira info for user {event.user_id}")

#             # Store refresh token
#             expires_at = datetime.now(timezone.utc) + timedelta(seconds=event.expires_in * 2)
#             refresh_token = RefreshTokenModel(
#                 token=event.refresh_token,
#                 user_id=event.user_id,
#                 token_type=TokenType.JIRA,
#                 cloud_id=event.cloud_id,
#                 scope=event.scope,
#                 expires_at=expires_at
#             )
#             await self.refresh_token_repository.create_refresh_token(refresh_token)

#             # Cache access token
#             await self.redis_service.cache_jira_token(
#                 user_id=event.user_id,
#                 access_token=event.access_token
#             )

#             log.info(f"Successfully processed Jira login for user {event.user_id}")
#         except Exception as e:
#             log.error(f"Error handling Jira login event: {str(e)}")
