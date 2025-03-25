from typing import Any, Dict, Optional

from src.configs.logger import log
from src.domain.models.nats.subscribes.jira_user import JiraUserChangeNATSSubscribeDTO
from src.domain.services.nats_message_handler import INATSMessageHandler
from src.domain.services.redis_service import IRedisService


class UserMessageHandler(INATSMessageHandler):
    def __init__(self, redis_service: IRedisService):
        self.redis_service = redis_service

    async def handle(self, subject: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle user events and clear related caches"""
        try:
            # Parse the event
            event = JiraUserChangeNATSSubscribeDTO.model_validate(message)

            log.info(f"Handling user event: {event.event_type} for user {event.user_id}")

            # Clear Jira token cache for the user
            await self.redis_service.delete(f"jira_token:{event.user_id}")

            # Clear Microsoft token cache for the user
            await self.redis_service.delete(f"microsoft_token:{event.user_id}")

            log.info(f"Cleared cache for user {event.user_id}")

            return None
        except Exception as e:
            log.error(f"Error in UserMessageHandler: {str(e)}")
            raise
