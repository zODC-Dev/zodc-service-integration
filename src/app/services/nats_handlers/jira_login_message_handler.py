from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from src.configs.logger import log
from src.domain.constants.refresh_tokens import TokenType
from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.database.refresh_token import RefreshTokenDBCreateDTO
from src.domain.models.nats.subscribes.jira_user import JiraUserLoginNATSSubscribeDTO
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.services.nats_message_handler import INATSMessageHandler
from src.domain.services.redis_service import IRedisService
from src.utils.jwt_utils import get_jwt_expiry


class JiraLoginMessageHandler(INATSMessageHandler):
    def __init__(
        self,
        user_repository: IJiraUserRepository,
        refresh_token_repository: IRefreshTokenRepository,
        redis_service: IRedisService
    ):
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        self.redis_service = redis_service

    async def handle(self, subject: str, message: Dict[str, Any]) -> None:
        try:
            event = JiraUserLoginNATSSubscribeDTO.model_validate(message)

            # Check if user exists
            user = await self.user_repository.get_user_by_id(event.user_id)

            if user:
                # Update Jira info if user exists
                user_update = JiraUserDBUpdateDTO(
                    is_system_user=True,
                    user_id=event.user_id,
                    jira_account_id=event.jira_account_id,
                    avatar_url=event.avatar_url
                )
                assert user.user_id is not None, "User ID is required"
                await self.user_repository.update_user(user.user_id, user_update)
                log.info(f"Updated Jira link for existing user {user.jira_account_id}")

            else:
                # Create new user with Jira info
                new_user = JiraUserDBCreateDTO(
                    email=event.email,
                    user_id=event.user_id,
                    jira_account_id=event.jira_account_id,
                    is_system_user=True,
                    is_active=True,
                    name=''
                )
                await self.user_repository.create_user(new_user)
                log.info(f"Created new user with Jira link for user {event.user_id}")

            # Store refresh token
            expires_at = get_jwt_expiry(event.refresh_token) or datetime.now(
                timezone.utc) + timedelta(seconds=event.expires_in * 2)
            refresh_token = RefreshTokenDBCreateDTO(
                token=event.refresh_token,
                user_id=event.user_id,
                token_type=TokenType.JIRA,
                expires_at=expires_at
            )
            await self.refresh_token_repository.create_refresh_token(refresh_token)

            # Cache access token
            await self.redis_service.cache_jira_token(
                user_id=event.user_id,
                access_token=event.access_token,
                expiry=event.expires_in
            )

            log.info(f"Successfully processed Jira login for user {event.user_id}")

        except Exception as e:
            log.error(f"Error handling Jira login event: {str(e)}")
