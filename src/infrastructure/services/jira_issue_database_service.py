from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.constants.jira import JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService


class JiraIssueDatabaseService(IJiraIssueDatabaseService):
    def __init__(
        self,
        issue_repository: IJiraIssueRepository,
    ):
        self.issue_repository = issue_repository

    async def get_issue(self, session: AsyncSession, user_id: int, issue_id: str) -> Optional[JiraIssueModel]:
        """Get issue from database by ID"""
        return await self.issue_repository.get_by_jira_issue_id(session, issue_id)

    async def get_issues_by_user_id(self, session: AsyncSession, user_id: int) -> List[JiraIssueModel]:
        """Get issues from database by user ID"""
        return await self.issue_repository.get_by_user_id(session, user_id)

    async def get_project_issues(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: Optional[int] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        """Get project issues from database with filters"""
        return await self.issue_repository.get_project_issues(
            session,
            project_key=project_key,
            sprint_id=sprint_id,
            is_backlog=is_backlog,
            issue_type=issue_type,
            search=search,
            limit=limit
        )

    async def get_issue_by_key(self, session: AsyncSession, issue_key: str) -> Optional[JiraIssueModel]:
        """Get issue by key from database"""
        return await self.issue_repository.get_by_jira_issue_key(session, issue_key)
