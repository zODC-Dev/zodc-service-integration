from abc import ABC, abstractmethod
from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.constants.jira import JiraIssueType
from src.domain.models.database.jira_issue import JiraIssueDBCreateDTO, JiraIssueDBUpdateDTO
from src.domain.models.jira_issue import JiraIssueModel


class IJiraIssueRepository(ABC):
    @abstractmethod
    async def get_by_jira_issue_id(self, session: AsyncSession, jira_issue_id: str) -> Optional[JiraIssueModel]:
        pass

    @abstractmethod
    async def get_by_user_id(self, session: AsyncSession, user_id: int) -> List[JiraIssueModel]:
        pass

    @abstractmethod
    async def update(self, session: AsyncSession, issue_id: str, issue_update: JiraIssueDBUpdateDTO) -> JiraIssueModel:
        pass

    @abstractmethod
    async def create(self, session: AsyncSession, issue: JiraIssueDBCreateDTO) -> JiraIssueModel:
        pass

    @abstractmethod
    async def get_all(self, session: AsyncSession) -> List[JiraIssueModel]:
        pass

    @abstractmethod
    async def get_project_issues(
        self,
        session: AsyncSession,
        project_key: str,
        sprint_id: Optional[int] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        pass

    @abstractmethod
    async def get_by_jira_issue_key(self, session: AsyncSession, jira_issue_key: str) -> Optional[JiraIssueModel]:
        pass

    @abstractmethod
    async def update_by_key(self, session: AsyncSession, jira_issue_key: str, issue_update: JiraIssueDBUpdateDTO) -> JiraIssueModel:
        pass

    @abstractmethod
    async def get_issues_by_keys(self, session: AsyncSession, keys: List[str]) -> List[JiraIssueModel]:
        """Get issues by their Jira keys

        Parameters:
        - session: Database session
        - keys: List of Jira issue keys (e.g., ["PROJ-1", "PROJ-2"])

        Returns:
        - List of Jira issues matching the provided keys
        """
        pass

    @abstractmethod
    async def reset_system_linked_for_sprint(self, session: AsyncSession, sprint_id: int) -> int:
        """Reset is_system_linked flag to False for all issues in a sprint

        Parameters:
        - session: Database session
        - sprint_id: The system ID of the sprint

        Returns:
        - The number of issues that were updated
        """
        pass
