from abc import ABC, abstractmethod
from typing import Any, Dict

from src.domain.models.jira_issue import JiraIssueModel


class IJiraIssueAPIService(ABC):
    @abstractmethod
    async def create_issue(self, user_id: int, issue_data: Dict[str, Any]) -> JiraIssueModel:
        pass

    @abstractmethod
    async def update_issue(self, user_id: int, issue_id: str, update: Dict[str, Any]) -> None:
        pass
