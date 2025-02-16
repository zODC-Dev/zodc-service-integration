from typing import List, Optional

from src.domain.constants.jira import JiraIssueType
from src.domain.entities.jira import JiraIssue, JiraIssueCreate, JiraIssueUpdate, JiraProject, JiraSprint
from src.domain.entities.jira_api import JiraCreateIssueResponse
from src.domain.services.jira_service import IJiraService


class JiraApplicationService:
    def __init__(self, jira_service: IJiraService):
        self.jira_service = jira_service

    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssue]:
        return await self.jira_service.get_project_issues(
            user_id=user_id,
            project_key=project_key,
            sprint_id=sprint_id,
            is_backlog=is_backlog,
            issue_type=issue_type,
            search=search,
            limit=limit
        )

    async def get_accessible_projects(self, user_id: int) -> List[JiraProject]:
        return await self.jira_service.get_accessible_projects(user_id)

    async def create_issue(self, user_id: int, issue: JiraIssueCreate) -> JiraCreateIssueResponse:
        return await self.jira_service.create_issue(user_id, issue)

    async def update_issue(
        self,
        user_id: int,
        issue_id: str,
        update: JiraIssueUpdate
    ) -> JiraIssue:
        """Update a Jira issue"""
        return await self.jira_service.update_issue(
            user_id=user_id,
            issue_id=issue_id,
            update=update
        )

    async def get_project_sprints(
        self,
        user_id: int,
        project_id: str,
    ) -> List[JiraSprint]:
        return await self.jira_service.get_project_sprints(
            user_id=user_id,
            project_id=project_id
        )
