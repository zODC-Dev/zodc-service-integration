from typing import Any, Dict

from src.configs.logger import log
from src.domain.constants.refresh_tokens import TokenType
from src.domain.entities.nats_event import NATSEventType, TokenEvent, UserEvent
from src.domain.entities.refresh_token import RefreshTokenEntity
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.repositories.user_repository import IUserRepository
from src.domain.services.nats_service import INATSService
from src.domain.services.redis_service import IRedisService


class NATSEventService:
    def __init__(self, nats_service: INATSService, redis_service: IRedisService, user_repository: IUserRepository, refresh_token_repository: IRefreshTokenRepository):
        self.nats_service = nats_service
        self.redis_service = redis_service
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository

    async def start_nats_subscribers(self) -> None:
        """Start NATS subscribers"""
        for event_type in NATSEventType:
            if event_type.startswith("user"):
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_user_event
                )
            elif event_type.startswith("auth"):
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_token_event
                )

    async def handle_user_event(self, subject: str, message: Dict[str, Any]) -> None:
        # Parse the event
        event = UserEvent.model_validate(message)

        """Handle user events and clear related caches"""
        log.info(f"Handling user event: {event.event_type} for user {event.user_id}")

        # Clear Jira token cache for the user
        await self.redis_service.delete(f"jira_token:{event.user_id}")

        # Clear Microsoft token cache for the user
        await self.redis_service.delete(f"microsoft_token:{event.user_id}")

        log.info(f"Cleared cache for user {event.user_id}")

    async def handle_token_event(self, subject: str, message: Dict[str, Any]) -> None:
        """Handle token events and clear related caches"""
        log.info(f"Handling token event: {subject} for user {message['user_id']}")

        # Parse the event
        event = TokenEvent.model_validate(message)

        # Cache access token
        if event.token_type == TokenType.MICROSOFT:
            await self.redis_service.cache_microsoft_token(
                user_id=event.user_id,
                access_token=event.access_token,
                expiry=event.expires_in
            )
        else:
            await self.redis_service.cache_jira_token(
                user_id=event.user_id,
                access_token=event.access_token,
                expiry=event.expires_in
            )

        # Store refresh token
        await self.refresh_token_repository.create_refresh_token(
            RefreshTokenEntity(
                token=event.refresh_token,
                user_id=event.user_id,
                token_type=event.token_type,
                expires_at=event.expires_at
            )
        )
