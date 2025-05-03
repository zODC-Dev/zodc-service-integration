from abc import ABC, abstractmethod
from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.constants.jira import JiraIssueType
from src.domain.models.database.jira_issue import JiraIssueDBCreateDTO, JiraIssueDBUpdateDTO
from src.domain.models.jira_issue import JiraIssueModel


class IJiraIssueDatabaseService(ABC):
    @abstractmethod
    async def get_issue(self, session: AsyncSession, user_id: int, issue_id: str) -> Optional[JiraIssueModel]:
        pass

    @abstractmethod
    async def get_issues_by_user_id(self, session: AsyncSession, user_id: int) -> List[JiraIssueModel]:
        pass

    @abstractmethod
    async def create_issue(
        self,
        session: AsyncSession,
        user_id: int,
        issue: JiraIssueDBCreateDTO
    ) -> JiraIssueModel:
        """Create a new Jira issue"""
        pass

    @abstractmethod
    async def update_issue(
        self,
        session: AsyncSession,
        user_id: int,
        issue_id: str,
        update: JiraIssueDBUpdateDTO
    ) -> JiraIssueModel:
        """Update an existing Jira issue"""
        pass

    @abstractmethod
    async def get_project_issues(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: Optional[int] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        """Get project issues from database"""
        pass

    @abstractmethod
    async def get_issue_by_key(self, session: AsyncSession, issue_key: str) -> Optional[JiraIssueModel]:
        """Get issue by key from database"""
        pass
