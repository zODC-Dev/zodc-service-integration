from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from src.infrastructure.dtos.jira.sprint_responses import JiraAPISprintResponse
from src.infrastructure.dtos.jira.user_responses import JiraAPIUserResponse

from .base import JiraAPIFieldsBase, JiraAPIResponseBase


class JiraAPIIssuePriorityResponse(JiraAPIResponseBase):
    id: str
    name: str
    icon_url: str = Field(alias="iconUrl")


class JiraAPIIssueTypeResponse(JiraAPIResponseBase):
    id: str
    name: str
    hierarchy_level: int = Field(alias="hierarchyLevel")
    icon_url: str = Field(alias="iconUrl")


class JiraAPIIssueStatusResponse(JiraAPIResponseBase):
    id: str
    name: str
    status_category: Dict[str, Any] = Field(alias="statusCategory")


class JiraAPIIssueFieldsResponse(JiraAPIFieldsBase):
    summary: str
    description: Optional[Dict[str, Any]]
    status: JiraAPIIssueStatusResponse
    assignee: Optional[JiraAPIUserResponse]
    reporter: Optional[JiraAPIUserResponse]
    priority: Optional[JiraAPIIssuePriorityResponse]
    issuetype: JiraAPIIssueTypeResponse
    created: datetime
    updated: datetime
    customfield_10016: Optional[float] = None  # Story points
    customfield_10017: Optional[float] = None  # Actual points
    customfield_10020: Optional[List[JiraAPISprintResponse]] = None  # Sprints


class JiraAPIIssueResponse(JiraAPIResponseBase):
    id: str
    key: str
    self: str
    fields: JiraAPIIssueFieldsResponse
