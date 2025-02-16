from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.constants.jira import JiraIssueType
from src.domain.entities.jira import JiraIssueCreate, JiraProject, JiraIssue, JiraIssueUpdate, JiraSprint
from src.domain.entities.jira_api import JiraCreateIssueResponse


class IJiraService(ABC):
    @abstractmethod
    async def get_project_issues(
        self,
        user_id: int,
        project_id: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        limit: int = 50
    ) -> List[JiraIssue]:
        """Get issues from a specific Jira project"""
        pass

    @abstractmethod
    async def get_accessible_projects(self, user_id: int) -> List[JiraProject]:
        """Get all projects that the user has access to"""
        pass

    @abstractmethod
    async def create_issue(
        self,
        user_id: int,
        issue: JiraIssueCreate
    ) -> JiraCreateIssueResponse:
        """Create a new Jira issue"""
        pass

    @abstractmethod
    async def update_issue(
        self,
        user_id: int,
        issue_id: str,
        update: JiraIssueUpdate
    ) -> JiraIssue:
        """Update an existing Jira issue"""
        pass

    @abstractmethod
    async def get_project_sprints(
        self,
        user_id: int,
        project_id: str,
    ) -> List[JiraSprint]:
        """Get all sprints from a specific Jira project"""
        pass
