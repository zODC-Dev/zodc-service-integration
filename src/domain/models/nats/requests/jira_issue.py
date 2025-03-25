from typing import List, Optional

from pydantic import BaseModel

from src.domain.constants.jira import JiraActionType, JiraIssueStatus, JiraIssueType


class JiraIssueSyncNATSRequestDTO(BaseModel):
    user_id: int
    project_key: str
    issue_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    type: Optional[JiraIssueType] = None
    status: Optional[JiraIssueStatus] = None
    assignee_id: Optional[int] = None  # Internal user id
    sprint_id: Optional[int] = None  # Jira sprint id (if not provided, issue will be created in backlog)
    estimate_point: Optional[float] = None
    actual_point: Optional[float] = None
    action_type: JiraActionType


class JiraIssueBatchSyncNATSRequestDTO(BaseModel):
    issues: List[JiraIssueSyncNATSRequestDTO]
