from typing import List, Optional

from src.domain.entities.jira import JiraIssueCreate, JiraProject, JiraTask, JiraTaskUpdate
from src.domain.entities.jira_api import JiraCreateIssueResponse
from src.domain.services.jira_service import IJiraService


class JiraApplicationService:
    def __init__(self, jira_service: IJiraService):
        self.jira_service = jira_service

    async def get_project_tasks(
        self,
        user_id: int,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraTask]:
        return await self.jira_service.get_project_tasks(
            user_id=user_id,
            project_id=project_id,
            status=status,
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
        update: JiraTaskUpdate
    ) -> JiraTask:
        """Update a Jira issue"""
        return await self.jira_service.update_issue(
            user_id=user_id,
            issue_id=issue_id,
            update=update
        )
