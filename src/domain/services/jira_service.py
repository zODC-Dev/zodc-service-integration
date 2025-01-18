from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.jira import JiraIssueCreate, JiraProject, JiraTask
from src.domain.entities.jira_api import JiraCreateIssueResponse


class IJiraService(ABC):
    @abstractmethod
    async def get_project_tasks(
        self,
        user_id: int,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraTask]:
        """Get tasks from a specific Jira project"""
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
