from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr, HttpUrl

from src.app.schemas.responses.base import BaseResponse


class MicrosoftCalendarEventResponse(BaseResponse):
    id: str
    subject: str
    start_time: datetime
    end_time: datetime
    organizer_email: EmailStr
    is_online_meeting: bool
    online_meeting_url: Optional[HttpUrl] = None
    attendees: List[EmailStr] = []
    description: Optional[str] = None
    location: Optional[str] = None
    time_zone: str = "UTC"

    class Config:
        from_attributes = True


class MicrosoftCalendarEventsResponse(BaseResponse):
    events: List[MicrosoftCalendarEventResponse]
    next_link: Optional[HttpUrl] = None

    class Config:
        from_attributes = True


class CreateCalendarEventResponse(BaseResponse):
    event_id: str
    subject: str
    start_time: datetime
    end_time: datetime
    online_meeting_url: Optional[HttpUrl] = None

    class Config:
        from_attributes = True


class UpdateCalendarEventResponse(BaseResponse):
    success: bool
    event_id: str
    message: str = "Event updated successfully"

    class Config:
        from_attributes = True


class DeleteCalendarEventResponse(BaseResponse):
    success: bool
    event_id: str
    message: str = "Event deleted successfully"

    class Config:
        from_attributes = True
