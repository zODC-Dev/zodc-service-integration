from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_serializer

from src.domain.constants.jira import JiraActionType, JiraIssueStatus, JiraIssueType


class JiraIssueSyncRequestDTO(BaseModel):
    user_id: int
    project_key: str
    issue_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    issue_type: Optional[JiraIssueType] = None
    status: Optional[JiraIssueStatus] = None
    assignee_id: Optional[int] = None  # Internal user id
    estimate_point: Optional[float] = None
    actual_point: Optional[float] = None
    action_type: JiraActionType


class JiraIssueSyncResponseDTO(BaseModel):
    success: bool
    action_type: JiraActionType
    issue_id: Optional[str] = None
    error_message: Optional[str] = None
    synced_at: datetime = Field(default_factory=datetime.now)

    @field_serializer("synced_at")
    def serialize_synced_at(self, synced_at: datetime, _info: Any) -> str:
        return synced_at.isoformat()


class JiraBatchSyncRequestDTO(BaseModel):
    issues: List[JiraIssueSyncRequestDTO]


class JiraBatchSyncResponseDTO(BaseModel):
    results: List[JiraIssueSyncResponseDTO]
