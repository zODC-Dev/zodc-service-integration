from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.domain.constants.jira import JiraIssueType


class JiraIssueResponse(BaseModel):
    id: str
    key: str
    summary: str
    description: Optional[str] = None
    status: str
    assignee: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    priority: Optional[str] = None
    issue_type: JiraIssueType


class JiraProjectResponse(BaseModel):
    id: str
    key: str
    name: str
    description: Optional[str] = None
    project_type: Optional[str] = None
    project_category: Optional[str] = None
    lead: Optional[str] = None
    url: Optional[str] = None


class JiraTaskResponse(BaseModel):
    id: str
    key: str
    summary: str
    description: Optional[str] = None
    status: str
    assignee: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class JiraCreateIssueResponse(BaseModel):
    id: str
    key: str
    self: str  # API URL of the created issue
