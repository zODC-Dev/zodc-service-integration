from abc import ABC, abstractmethod

from src.domain.models.jira_issue import JiraIssueCreateDTO, JiraIssueModel, JiraIssueUpdateDTO


class IJiraIssueDatabaseService(ABC):
    @abstractmethod
    async def get_issue(self, user_id: int, issue_id: str) -> JiraIssueModel:
        pass

    @abstractmethod
    async def create_issue(
        self,
        user_id: int,
        issue: JiraIssueCreateDTO
    ) -> JiraIssueModel:
        """Create a new Jira issue"""
        pass

    @abstractmethod
    async def update_issue(
        self,
        user_id: int,
        issue_id: str,
        update: JiraIssueUpdateDTO
    ) -> JiraIssueModel:
        """Update an existing Jira issue"""
        pass

    # @abstractmethod
    # async def get_project_issues(
    #     self,
    #     user_id: int,
    #     project_key: str,
    #     sprint_id: Optional[str] = None,
    #     is_backlog: Optional[bool] = None,
    #     issue_type: Optional[JiraIssueType] = None,
    #     search: Optional[str] = None,
    #     limit: int = 50
    # ) -> List[JiraIssueModel]:
    #     pass
