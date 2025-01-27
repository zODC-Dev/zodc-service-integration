from typing import Any, Dict

from src.app.services.user_event_service import UserEventService
from src.configs.logger import log
from src.domain.entities.user_events import UserEvent


class UserEventHandler:
    def __init__(self, user_event_service: UserEventService):
        self.user_event_service = user_event_service

    async def handle_message(self, subject: str, message: Dict[str, Any]) -> None:
        try:
            # Parse the event
            event = UserEvent.model_validate(message)

            # Handle the event
            await self.user_event_service.handle_user_event(event)

        except Exception as e:
            log.error(f"Error handling user event: {str(e)}")
