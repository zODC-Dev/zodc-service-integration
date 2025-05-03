from abc import ABC, abstractmethod
from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.constants.jira import JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_project import JiraProjectModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class IJiraProjectAPIService(ABC):
    @abstractmethod
    async def get_accessible_projects(self, session: AsyncSession, user_id: int) -> List[JiraProjectModel]:
        """Get all accessible Jira projects from API"""
        pass

    @abstractmethod
    async def get_project_sprints(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str
    ) -> List[JiraSprintModel]:
        """Get all sprints in a project from API"""
        pass

    @abstractmethod
    async def get_project_issues(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50,
        start_at: int = 0
    ) -> List[JiraIssueModel]:
        """Get all issues in a project from API"""
        pass

    @abstractmethod
    async def get_project_details(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str
    ) -> JiraProjectModel:
        """Get project details from API"""
        pass

    @abstractmethod
    async def get_project_users(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str
    ) -> List[JiraUserModel]:
        """Get all users in a project from API"""
        pass
