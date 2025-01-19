from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.app.controllers.microsoft_calendar_controller import MicrosoftCalendarController
from src.app.dependencies.microsoft_calendar import get_microsoft_calendar_controller
from src.app.schemas.responses.microsoft_calendar import MicrosoftCalendarEventsResponse

router = APIRouter()


@router.get("/events", response_model=MicrosoftCalendarEventsResponse)
# @require_permissions(permissions=["calendar.read"], scope="system")
async def get_calendar_events(
    user_id: int,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    page_size: int = Query(50, ge=1, le=100),
    next_link: Optional[str] = Query(None),
    controller: MicrosoftCalendarController = Depends(get_microsoft_calendar_controller),
) -> MicrosoftCalendarEventsResponse:
    """Get user's calendar events"""
    events = await controller.get_user_events(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        page_size=page_size,
        next_link=next_link
    )
    return events
