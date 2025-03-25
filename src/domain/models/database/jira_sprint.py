from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class JiraSprintDBCreateDTO(BaseModel):
    jira_sprint_id: int
    name: str
    state: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    complete_date: Optional[datetime] = None
    project_key: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_dump(self) -> dict:
        data = super().model_dump()
        # Ensure all datetime fields have timezone info
        datetime_fields = ['start_date', 'end_date', 'complete_date', 'created_at']
        for field in datetime_fields:
            if data.get(field) and data[field].tzinfo is None:
                data[field] = data[field].replace(tzinfo=timezone.utc)
        return data


class JiraSprintDBUpdateDTO(BaseModel):
    name: str
    state: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    complete_date: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def model_dump(self) -> dict:
        data = super().model_dump()
        # Ensure all datetime fields have timezone info
        for field in ['start_date', 'end_date', 'complete_date', 'updated_at']:
            if data.get(field) and data[field].tzinfo is None:
                data[field] = data[field].replace(tzinfo=timezone.utc)
        return data
