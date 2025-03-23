from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.domain.constants.jira import JiraActionType, JiraIssueStatus, JiraIssueType


class JiraIssueSyncRequestDTO(BaseModel):
    user_id: int
    project_key: str
    issue_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    issue_type: Optional[JiraIssueType] = None
    status: Optional[JiraIssueStatus] = None
    assignee_id: Optional[int] = None
    estimate_points: Optional[float] = None
    actual_points: Optional[float] = None
    action_type: JiraActionType


class JiraIssueSyncResponseDTO(BaseModel):
    success: bool
    action_type: JiraActionType
    issue_id: Optional[str] = None
    error_message: Optional[str] = None
    synced_at: datetime = Field(default_factory=datetime.utcnow)


class JiraBatchSyncRequestDTO(BaseModel):
    issues: List[JiraIssueSyncRequestDTO]


class JiraBatchSyncResponseDTO(BaseModel):
    results: List[JiraIssueSyncResponseDTO]
