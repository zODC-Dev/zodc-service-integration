from datetime import datetime, timezone
from typing import Optional

from src.infrastructure.dtos.jira.base import JiraAPIResponseBase


class JiraAPISprintResponse(JiraAPIResponseBase):
    id: int
    name: str
    state: str
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    completeDate: Optional[datetime] = None
    goal: Optional[str] = None

    class Config:
        extra = "allow"
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def ensure_timezone(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime has timezone info"""
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @property
    def start_date(self) -> Optional[datetime]:
        return self.ensure_timezone(self.startDate)

    @property
    def end_date(self) -> Optional[datetime]:
        return self.ensure_timezone(self.endDate)

    @property
    def complete_date(self) -> Optional[datetime]:
        return self.ensure_timezone(self.completeDate)
