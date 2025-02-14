from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class JiraResponseBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )


class JiraAssigneeResponse(JiraResponseBase):
    account_id: str
    email_address: str
    avatar_urls: str
    display_name: str


class JiraIssuePriorityResponse(JiraResponseBase):
    id: str
    icon_url: str
    name: str


class JiraIssueSprintResponse(JiraResponseBase):
    id: int
    name: str
    state: str  # active, closed, future


class JiraIssueResponse(JiraResponseBase):
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


class JiraProjectResponse(JiraResponseBase):
    id: str
    key: str
    name: str
    description: Optional[str] = None
    project_type: Optional[str] = None
    project_category: Optional[str] = None
    lead: Optional[str] = None
    url: Optional[str] = None


class JiraSprintResponse(JiraResponseBase):
    id: int
    name: str
    state: str  # active, closed, future


class JiraCreateIssueResponse(JiraResponseBase):
    id: str
    key: str
    self: str  # API URL of the created issue
