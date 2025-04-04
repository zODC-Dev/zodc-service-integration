from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from src.domain.models.jira.apis.responses.base import JiraAPIFieldsBase, JiraAPIResponseBase
from src.domain.models.jira.apis.responses.common import JiraAPIIssuePriorityResponse
from src.domain.models.jira.apis.responses.jira_sprint import JiraSprintAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO


class JiraAPIIssueTypeResponse(JiraAPIResponseBase):
    id: str
    name: str
    hierarchy_level: int = Field(alias="hierarchyLevel")
    icon_url: str = Field(alias="iconUrl")


class JiraAPIIssueStatusResponse(JiraAPIResponseBase):
    id: str
    name: str
    status_category: Dict[str, Any] = Field(alias="statusCategory")


class JiraAPIProjectResponse(JiraAPIResponseBase):
    self: str
    id: str
    key: str
    name: str
    projectTypeKey: str
    simplified: bool
    avatarUrls: Dict[str, str]


class JiraAPIIssueFieldsResponse(JiraAPIFieldsBase):
    summary: str
    description: Optional[Dict[str, Any]]
    status: JiraAPIIssueStatusResponse
    assignee: Optional[JiraUserAPIGetResponseDTO]
    reporter: Optional[JiraUserAPIGetResponseDTO]
    priority: Optional[JiraAPIIssuePriorityResponse]
    project: Optional[JiraAPIProjectResponse]
    issuetype: JiraAPIIssueTypeResponse
    created: datetime
    updated: datetime
    customfield_10016: Optional[float] = None  # Story points
    customfield_10017: Optional[float] = None  # Actual points
    customfield_10020: Optional[List[JiraSprintAPIGetResponseDTO]] = None  # Sprints


class JiraIssueAPIGetResponseDTO(JiraAPIResponseBase):
    id: str
    key: str
    self: str
    fields: JiraAPIIssueFieldsResponse
