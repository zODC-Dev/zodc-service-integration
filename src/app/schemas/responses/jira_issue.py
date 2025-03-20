from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.app.schemas.responses.base import BaseResponse
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType


class JiraAssigneeResponse(BaseModel):
    id: Optional[int] = None
    jira_account_id: str
    email: str
    avatar_url: str
    name: str
    is_system_user: bool


class JiraIssuePriorityResponse(BaseModel):
    id: str
    name: str
    icon_url: str


class JiraIssueSprintResponse(BaseModel):
    id: int
    name: str
    state: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    goal: Optional[str] = None


class GetJiraIssueResponse(BaseResponse):
    id: str
    key: str
    summary: str
    assignee: Optional[JiraAssigneeResponse] = None
    priority: Optional[JiraIssuePriorityResponse] = None
    type: JiraIssueType
    sprint: Optional[JiraIssueSprintResponse] = None
    estimate_point: float = 0
    actual_point: Optional[float] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    status: JiraIssueStatus


class JiraCreateIssueResponse(BaseResponse):
    id: str
    key: str
    self: str  # API URL of the created issue
