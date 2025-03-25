from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.jira.apis.requests.jira_issue import JiraIssueAPICreateRequestDTO, JiraIssueAPIUpdateRequestDTO
from src.domain.models.jira_issue import JiraIssueModel


class IJiraIssueAPIService(ABC):
    @abstractmethod
    async def create_issue(self, user_id: int, issue_data: JiraIssueAPICreateRequestDTO) -> JiraIssueModel:
        pass

    @abstractmethod
    async def update_issue(self, user_id: int, issue_id: str, update: JiraIssueAPIUpdateRequestDTO) -> JiraIssueModel:
        pass

    @abstractmethod
    async def get_issue(self, user_id: int, issue_id: str) -> JiraIssueModel:
        pass

    @abstractmethod
    async def search_issues(self, user_id: int, jql: str, start_at: int = 0, max_results: int = 50, fields: Optional[List[str]] = None) -> List[JiraIssueModel]:
        pass
