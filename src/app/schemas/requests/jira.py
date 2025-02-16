from typing import List, Optional

from fastapi import Query

from src.domain.constants.jira import JiraIssueType, JiraIssueStatus
from src.app.schemas.requests.base import BaseRequest


class JiraIssueCreateRequest(BaseRequest):
    project_key: str
    summary: str
    description: Optional[str] = None
    issue_type: JiraIssueType
    priority: Optional[str] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    epic_link: Optional[str] = None


class JiraIssueUpdateRequest(BaseRequest):
    assignee: Optional[str] = None
    status: Optional[JiraIssueStatus] = None
    estimate_points: Optional[float] = None
    actual_points: Optional[float] = None


class JiraIssueGetRequest(BaseRequest):
    project_key: str
    issue_id: str
    sprint_id: Optional[str] = Query(None, description="Filter by sprint number (use 'backlog' for backlog items)")
    issue_type: Optional[JiraIssueType] = Query(None, description="Filter by issue type (Bug, Task, Story, Epic)")
    limit: int = Query(50, ge=1, le=100)
