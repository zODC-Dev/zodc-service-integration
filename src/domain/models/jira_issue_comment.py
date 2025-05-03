from datetime import datetime

from pydantic import BaseModel

from src.domain.models.jira_user import JiraUserModel


class JiraIssueCommentModel(BaseModel):
    """Model for Jira issue comment"""
    id: str
    assignee: JiraUserModel
    content: str
    created_at: datetime
