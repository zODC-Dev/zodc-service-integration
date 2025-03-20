from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.constants.jira import JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_project import JiraProjectModel, JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class IJiraProjectService(ABC):
    @abstractmethod
    async def get_accessible_projects(self, user_id: int) -> List[JiraProjectModel]:
        pass

    @abstractmethod
    async def get_project_sprints(self, user_id: int, project_id: str) -> List[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_project_users(self, user_id: int, project_key: str) -> List[JiraUserModel]:
        pass

    @abstractmethod
    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        pass
