from typing import List, Optional

from pydantic import BaseModel

from src.domain.constants.jira import JiraIssueType


class JiraIssueCreateRequest(BaseModel):
    project_key: str
    summary: str
    description: Optional[str] = None
    issue_type: JiraIssueType
    priority: Optional[str] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    epic_link: Optional[str] = None
