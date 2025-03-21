from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.constants.jira import JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel


class IJiraIssueRepository(ABC):
    @abstractmethod
    async def get_by_jira_issue_id(self, jira_issue_id: str) -> Optional[JiraIssueModel]:
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

    @abstractmethod
    async def get_project_issues(
        self,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        pass
