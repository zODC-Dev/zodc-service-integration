from abc import ABC, abstractmethod
from typing import Any, Dict, List

from src.domain.models.jira_issue import JiraIssueModel


class IJiraIssueAPIService(ABC):
    @abstractmethod
    async def get_issue_details(self, user_id: int, issue_id: str) -> JiraIssueModel:
        pass

    @abstractmethod
    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        start_at: int = 0,
        max_results: int = 50
    ) -> List[JiraIssueModel]:
        pass

    @abstractmethod
    async def create_issue(self, user_id: int, issue_data: Dict[str, Any]) -> JiraIssueModel:
        pass

    @abstractmethod
    async def update_issue(self, user_id: int, issue_id: str, issue_data: Dict[str, Any]) -> None:
        pass
