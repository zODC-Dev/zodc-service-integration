from datetime import datetime
from typing import Optional

from fastapi import HTTPException

from src.app.schemas.responses.microsoft_calendar import MicrosoftCalendarEventsResponse
from src.app.services.microsoft_calendar_service import MicrosoftCalendarApplicationService
from src.configs.logger import log
from src.domain.exceptions.microsoft_calendar_exceptions import CalendarError


class MicrosoftCalendarController:
    def __init__(self, calendar_service: MicrosoftCalendarApplicationService):
        self.calendar_service = calendar_service

    async def get_user_events(
        self,
        user_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page_size: int = 50,
        next_link: Optional[str] = None
    ) -> MicrosoftCalendarEventsResponse:
        try:
            events = await self.calendar_service.get_user_events(
                user_id=user_id,
                start_time=start_time,
                end_time=end_time,
                page_size=page_size,
                next_link=next_link
            )
            return MicrosoftCalendarEventsResponse(**events.model_dump())
        except CalendarError as e:
            log.error(f"Calendar error: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            log.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")
