from typing import List, Optional

from pydantic import BaseModel

from src.domain.constants.jira import JiraIssueType, JiraIssueStatus


class JiraIssueCreateRequest(BaseModel):
    project_key: str
    summary: str
    description: Optional[str] = None
    issue_type: JiraIssueType
    priority: Optional[str] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    epic_link: Optional[str] = None


class JiraIssueUpdateRequest(BaseModel):
    assignee: Optional[str] = None
    status: Optional[JiraIssueStatus] = None
    estimate_points: Optional[float] = None
    actual_points: Optional[float] = None
