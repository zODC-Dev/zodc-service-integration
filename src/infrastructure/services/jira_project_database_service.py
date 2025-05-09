from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.database.jira_project import JiraProjectDBCreateDTO, JiraProjectDBUpdateDTO
from src.domain.models.jira_project import JiraProjectModel
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.services.jira_project_database_service import IJiraProjectDatabaseService


class JiraProjectDatabaseService(IJiraProjectDatabaseService):
    def __init__(self, project_repository: IJiraProjectRepository):
        self.project_repository = project_repository

    async def get_project(self, session: AsyncSession, project_id: int) -> Optional[JiraProjectModel]:
        return await self.project_repository.get_project_by_id(session, project_id)

    async def get_project_by_key(self, session: AsyncSession, key: str) -> Optional[JiraProjectModel]:
        return await self.project_repository.get_project_by_key(session, key)

    async def get_all_projects(self, session: AsyncSession) -> List[JiraProjectModel]:
        return await self.project_repository.get_all_projects(session)

    async def create_project(self, session: AsyncSession, project_data: JiraProjectDBCreateDTO) -> JiraProjectModel:
        return await self.project_repository.create_project(session, project_data)

    async def update_project(
        self,
        session: AsyncSession,
        project_id: int,
        project_data: JiraProjectDBUpdateDTO
    ) -> JiraProjectModel:
        return await self.project_repository.update_project(session, project_id, project_data)

    async def delete_project(self, session: AsyncSession, project_id: int) -> None:
        await self.project_repository.delete_project(session, project_id)

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
    #     """Get project issues from database with filters"""
    #     # Build query conditions
    #     conditions = [("project_key", project_key)]

    #     if sprint_id:
    #         conditions.append(("sprint_id", sprint_id))

    #     if is_backlog is not None:
    #         conditions.append(("sprint_id", None if is_backlog else {"$ne": None}))

    #     if issue_type:
    #         conditions.append(("issue_type", issue_type.value))

    #     if search:
    #         conditions.append(("summary", {"$regex": search, "$options": "i"}))

    #     # Get issues from repository
    #     return await self.project_repository.get_issues_by_conditions(
    #         conditions=conditions,
    #         limit=limit
    #     )

    async def get_user_projects(self, session: AsyncSession, user_id: int) -> List[JiraProjectModel]:
        """Get all projects for a specific user"""
        return await self.project_repository.get_projects_by_user_id(session, user_id)
