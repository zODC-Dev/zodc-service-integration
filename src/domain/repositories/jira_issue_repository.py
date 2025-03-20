from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.jira_issue import JiraIssueModel


class IJiraIssueRepository(ABC):
    @abstractmethod
    async def get_by_jira_id(self, jira_id: str) -> Optional[JiraIssueModel]:
        pass

    @abstractmethod
    async def update(self, issue: JiraIssueModel) -> JiraIssueModel:
        pass

    @abstractmethod
    async def create(self, issue: JiraIssueModel) -> JiraIssueModel:
        pass

    @abstractmethod
    async def get_all(self) -> List[JiraIssueModel]:
        pass
