from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from src.configs.logger import log
from src.domain.constants.refresh_tokens import TokenType
from src.domain.models.database.jira_user import JiraUserDBCreateDTO
from src.domain.models.database.refresh_token import RefreshTokenDBCreateDTO
from src.domain.models.nats.subscribes.jira_user import MicrosoftUserLoginNATSSubscribeDTO
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
            event = MicrosoftUserLoginNATSSubscribeDTO(**message)

            # Check if user exists
            user = await self.user_repository.get_user_by_id(event.user_id)
            if not user:
                new_user = JiraUserDBCreateDTO(
                    email=event.email,
                    user_id=event.user_id,
                    is_system_user=True,
                    is_active=True,
                    name=event.name
                )
                user = await self.user_repository.create_user(new_user)
                # log.warning(f"User not found for Microsoft login for user {event.user_id}")
                # return

            # Store refresh token
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=event.expires_in * 2)
            refresh_token = RefreshTokenDBCreateDTO(
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
