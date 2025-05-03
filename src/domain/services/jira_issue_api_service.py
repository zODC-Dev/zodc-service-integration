from abc import ABC, abstractmethod
from typing import List, Optional, Union

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.constants.jira import JiraIssueStatus
from src.domain.models.jira.apis.requests.jira_issue import JiraIssueAPICreateRequestDTO, JiraIssueAPIUpdateRequestDTO
from src.domain.models.jira.apis.responses.jira_changelog import (
    JiraIssueChangelogAPIGetResponseDTO,
    JiraIssueChangelogBulkFetchAPIGetResponseDTO,
)
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_issue_link import JiraIssueLinkModel


class IJiraIssueAPIService(ABC):
    @abstractmethod
    async def create_issue(self, session: AsyncSession, user_id: int, issue_data: JiraIssueAPICreateRequestDTO) -> JiraIssueModel:
        pass

    @abstractmethod
    async def update_issue(self, session: AsyncSession, user_id: int, issue_id: str, update: JiraIssueAPIUpdateRequestDTO) -> JiraIssueModel:
        pass

    @abstractmethod
    async def get_issue(self, session: AsyncSession, user_id: int, issue_id: str) -> Optional[JiraIssueModel]:
        pass

    @abstractmethod
    async def get_issue_with_admin_auth(self, issue_id: str) -> Optional[JiraIssueModel]:
        """Get issue using admin auth"""
        pass

    @abstractmethod
    async def create_issue_with_admin_auth(self, session: AsyncSession, issue_data: JiraIssueAPICreateRequestDTO) -> JiraIssueModel:
        """Create new issue using admin auth"""
        pass

    @abstractmethod
    async def update_issue_with_admin_auth(self, session: AsyncSession, issue_id: str, update: JiraIssueAPIUpdateRequestDTO) -> JiraIssueModel:
        """Update issue using admin auth"""
        pass

    @abstractmethod
    async def create_issue_link_with_admin_auth(self, source_issue_id: str, target_issue_id: str, relationship: str) -> bool:
        """Create issue link using admin auth"""
        pass

    @abstractmethod
    async def search_issues(self, user_id: int, jql: str, start_at: int = 0, max_results: int = 50, fields: Optional[List[str]] = None) -> List[JiraIssueModel]:
        pass

    @abstractmethod
    async def create_issue_link(self, session: AsyncSession, user_id: int, source_issue_id: str, target_issue_id: str, relationship: str) -> bool:
        pass

    @abstractmethod
    async def get_issue_changelog(self, session: AsyncSession, issue_id: str) -> JiraIssueChangelogAPIGetResponseDTO:
        """Lấy lịch sử thay đổi của issue từ Jira API"""
        pass

    @abstractmethod
    async def transition_issue_with_admin_auth(self, issue_id: str, status: Union[JiraIssueStatus, str]) -> bool:
        """Transition issue using admin auth"""
        pass

    @abstractmethod
    async def delete_issue_link_with_admin_auth(self, link_id: str) -> bool:
        """Delete an issue link by its ID using admin authentication"""
        pass

    @abstractmethod
    async def bulk_get_issue_changelog_with_admin_auth(self, issue_ids: List[str]) -> JiraIssueChangelogBulkFetchAPIGetResponseDTO:
        """Bulk get issue changelog with admin auth"""
        pass

    @abstractmethod
    async def bulk_get_issues_with_admin_auth(self, issue_ids: List[str]) -> List[JiraIssueModel]:
        """Bulk get issues with admin auth"""
        pass

    @abstractmethod
    async def update_issue_assignee_with_admin_auth(self, issue_key: str, assignee_account_id: str) -> bool:
        """Update the assignee of a Jira issue

        Args:
            issue_key: The Jira issue key
            assignee_account_id: The Jira account ID of the new assignee

        Returns:
            bool: Whether the update was successful
        """
        pass

    @abstractmethod
    async def get_issue_links_with_admin_auth(self, issue_key: str) -> List[JiraIssueLinkModel]:
        """Get links for an issue using admin auth

        Args:
            issue_key: The key of the issue to get links for

        Returns:
            List of issue link models
        """
        pass
