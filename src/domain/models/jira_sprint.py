from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class JiraSprintModel(BaseModel):
    id: Optional[int] = None
    jira_sprint_id: int
    name: str
    state: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    complete_date: Optional[datetime] = None
    goal: Optional[str] = None
    board_id: Optional[int] = None
    project_key: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    def ensure_timezone(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime has timezone info"""
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @property
    def start_date_tz(self) -> Optional[datetime]:
        return self.ensure_timezone(self.start_date)

    @property
    def end_date_tz(self) -> Optional[datetime]:
        return self.ensure_timezone(self.end_date)

    @property
    def complete_date_tz(self) -> Optional[datetime]:
        return self.ensure_timezone(self.complete_date)
