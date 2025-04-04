from datetime import datetime
from typing import Optional

from src.domain.models.microsoft_calendar_event import MicrosoftCalendarEventsList
from src.domain.services.microsoft_calendar_service import IMicrosoftCalendarService


class MicrosoftCalendarApplicationService:
    def __init__(self, calendar_service: IMicrosoftCalendarService):
        self.calendar_service = calendar_service

    async def get_user_events(
        self,
        user_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page_size: int = 50,
        next_link: Optional[str] = None
    ) -> MicrosoftCalendarEventsList:
        return await self.calendar_service.get_user_events(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            page_size=page_size,
            next_link=next_link
        )
