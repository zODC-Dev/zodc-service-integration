from typing import Optional

from src.app.schemas.responses.base import BaseResponse


class JiraAssigneeResponse(BaseResponse):
    id: int
    email: str
    avatar_url: str
    name: str
    is_system_user: bool


class JiraIssuePriorityResponse(BaseResponse):
    id: str
    icon_url: str
    name: str


class JiraIssueSprintResponse(BaseResponse):
    id: int
    name: str
    state: str  # active, closed, future


class JiraIssueResponse(BaseResponse):
    id: str
    key: str
    summary: str
    assignee: Optional[JiraAssigneeResponse] = None
    priority: Optional[JiraIssuePriorityResponse] = None
    type: str  # Will be converted from JiraIssueType enum
    sprint: Optional[JiraIssueSprintResponse] = None
    estimate_point: float = 0
    actual_point: Optional[float] = None
    description: Optional[str] = None
    created: str
    status: str  # Will be converted from JiraIssueStatus enum
    updated: str


class JiraProjectResponse(BaseResponse):
    id: str
    key: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    is_jira_linked: bool = False


class JiraSprintResponse(BaseResponse):
    id: int
    name: str
    state: str  # active, closed, future


class JiraCreateIssueResponse(BaseResponse):
    id: str
    key: str
    self: str  # API URL of the created issue
