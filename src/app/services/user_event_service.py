from src.configs.logger import log
from src.domain.entities.user_events import UserEvent
from src.infrastructure.services.redis_service import RedisService


class UserEventService:
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service

    async def handle_user_event(self, event: UserEvent) -> None:
        """Handle user events and clear related caches"""
        log.info(f"Handling user event: {event.event_type} for user {event.user_id}")

        # Clear Jira token cache for the user
        await self.redis_service.delete(f"jira_token:{event.user_id}")

        log.info(f"Cleared cache for user {event.user_id}")
