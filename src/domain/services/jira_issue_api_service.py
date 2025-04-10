from abc import ABC, abstractmethod
from typing import List, Optional, Union

from src.domain.constants.jira import JiraIssueStatus
from src.domain.models.jira.apis.requests.jira_issue import JiraIssueAPICreateRequestDTO, JiraIssueAPIUpdateRequestDTO
from src.domain.models.jira.apis.responses.jira_changelog import JiraIssueChangelogAPIGetResponseDTO
from src.domain.models.jira_issue import JiraIssueModel


class IJiraIssueAPIService(ABC):
    @abstractmethod
    async def create_issue(self, user_id: int, issue_data: JiraIssueAPICreateRequestDTO) -> JiraIssueModel:
        pass

    @abstractmethod
    async def update_issue(self, user_id: int, issue_id: str, update: JiraIssueAPIUpdateRequestDTO) -> JiraIssueModel:
        pass

    @abstractmethod
    async def get_issue(self, user_id: int, issue_id: str) -> Optional[JiraIssueModel]:
        pass

    @abstractmethod
    async def get_issue_with_admin_auth(self, issue_id: str) -> Optional[JiraIssueModel]:
        """Get issue using admin auth"""
        pass

    @abstractmethod
    async def create_issue_with_admin_auth(self, issue_data: JiraIssueAPICreateRequestDTO) -> JiraIssueModel:
        """Create new issue using admin auth"""
        pass

    @abstractmethod
    async def update_issue_with_admin_auth(self, issue_id: str, update: JiraIssueAPIUpdateRequestDTO) -> JiraIssueModel:
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
    async def create_issue_link(self, user_id: int, source_issue_id: str, target_issue_id: str, relationship: str) -> bool:
        pass

    @abstractmethod
    async def get_issue_changelog(self, issue_id: str) -> JiraIssueChangelogAPIGetResponseDTO:
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
