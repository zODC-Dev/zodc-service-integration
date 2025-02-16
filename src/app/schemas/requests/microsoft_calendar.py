from datetime import datetime
from typing import List, Optional

from pydantic import EmailStr

from src.app.schemas.requests.base import BaseRequest


class CreateCalendarEventRequest(BaseRequest):
    subject: str
    start_time: datetime
    end_time: datetime
    is_online_meeting: bool = False
    attendees: Optional[List[EmailStr]] = None
    description: Optional[str] = None
    location: Optional[str] = None
    time_zone: Optional[str] = "UTC"


class UpdateCalendarEventRequest(BaseRequest):
    subject: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_online_meeting: Optional[bool] = None
    attendees: Optional[List[EmailStr]] = None
    description: Optional[str] = None
    location: Optional[str] = None
    time_zone: Optional[str] = None
