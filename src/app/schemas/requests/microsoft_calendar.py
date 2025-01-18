from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, HttpUrl


class CreateCalendarEventRequest(BaseModel):
    subject: str
    start_time: datetime
    end_time: datetime
    is_online_meeting: bool = False
    attendees: Optional[List[EmailStr]] = None
    description: Optional[str] = None
    location: Optional[str] = None
    time_zone: Optional[str] = "UTC"


class UpdateCalendarEventRequest(BaseModel):
    subject: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_online_meeting: Optional[bool] = None
    attendees: Optional[List[EmailStr]] = None
    description: Optional[str] = None
    location: Optional[str] = None
    time_zone: Optional[str] = None
