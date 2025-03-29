from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_serializer

from src.domain.constants.jira import JiraSprintState


class JiraSprintDBCreateDTO(BaseModel):
    jira_sprint_id: int
    name: str
    state: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    complete_date: Optional[datetime] = None
    goal: Optional[str] = None
    board_id: Optional[int] = None
    project_key: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False

    @field_serializer('state')
    def serialize_state(self, state: str) -> str:
        return JiraSprintState.from_str(state).value

    def model_dump(self) -> Dict[str, Any]:
        data = super().model_dump()
        # Ensure all datetime fields have timezone info
        datetime_fields = ['start_date', 'end_date', 'complete_date', 'created_at', 'updated_at']
        for field in datetime_fields:
            if data.get(field) and data[field].tzinfo is None:
                data[field] = data[field].replace(tzinfo=timezone.utc)
        return data


class JiraSprintDBUpdateDTO(BaseModel):
    name: Optional[str] = None
    state: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    complete_date: Optional[datetime] = None
    goal: Optional[str] = None
    board_id: Optional[int] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False

    @field_serializer('state')
    def serialize_state(self, state: Optional[str]) -> Optional[str]:
        return JiraSprintState.from_str(state).value if state else None

    def model_dump(self) -> Dict[str, Any]:
        data = super().model_dump()
        # Ensure all datetime fields have timezone info
        for field in ['start_date', 'end_date', 'complete_date', 'updated_at']:
            if data.get(field) and data[field].tzinfo is None:
                data[field] = data[field].replace(tzinfo=timezone.utc)
        return data
