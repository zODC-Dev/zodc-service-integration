from typing import List, Optional

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.exceptions.project_exceptions import ProjectNotFoundError
from src.domain.models.database.jira_project import JiraProjectDBCreateDTO, JiraProjectDBUpdateDTO
from src.domain.models.jira_project import JiraProjectModel
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.infrastructure.entities.jira_project import JiraProjectEntity


class SQLAlchemyJiraProjectRepository(IJiraProjectRepository):
    def __init__(self):
        pass

    def _to_domain(self, entity: JiraProjectEntity) -> JiraProjectModel:
        model = JiraProjectModel(
            id=entity.id,
            jira_project_id=entity.jira_project_id,
            key=entity.key,
            name=entity.name,
            description=entity.description,
            avatar_url=entity.avatar_url
        )
        return model

    async def create_project(self, session: AsyncSession, project_data: JiraProjectDBCreateDTO) -> JiraProjectModel:
        project = JiraProjectEntity(
            jira_project_id=project_data.jira_project_id,
            key=project_data.key,
            name=project_data.name,
            description=project_data.description,
            avatar_url=project_data.avatar_url,
            user_id=project_data.user_id,
            project_id=project_data.project_id
        )
        session.add(project)
        await session.flush()
        await session.refresh(project)
        return self._to_domain(project)

    async def get_project_by_id(self, session: AsyncSession, project_id: int) -> Optional[JiraProjectModel]:
        project = await session.get(JiraProjectEntity, project_id)
        return self._to_domain(project) if project else None

    async def get_project_by_key(self, session: AsyncSession, key: str) -> Optional[JiraProjectModel]:
        result = await session.exec(
            select(JiraProjectEntity).where(col(JiraProjectEntity.key) ==
                                            key.upper())
        )
        project = result.first()
        return self._to_domain(project) if project else None

    async def get_all_projects(self, session: AsyncSession) -> List[JiraProjectModel]:
        result = await session.exec(select(JiraProjectEntity))
        projects = result.all()
        return [self._to_domain(p) for p in projects]

    async def update_project(self, session: AsyncSession, project_id: int, project_data: JiraProjectDBUpdateDTO) -> JiraProjectModel:
        project = await session.get(JiraProjectEntity, project_id)
        if project:
            if project_data.name is not None:
                project.name = project_data.name
            if project_data.key is not None:
                project.key = project_data.key
            if project_data.description is not None:
                project.description = project_data.description

            session.add(project)
            # Let the session manager handle the transaction
            await session.flush()

            await session.refresh(project)
            return self._to_domain(project)
        else:
            raise ProjectNotFoundError(
                f"Project with id {project_id} not found")

    async def delete_project(self, session: AsyncSession, project_id: int) -> None:
        project = await session.get(JiraProjectEntity, project_id)
        if project:
            await session.delete(project)
            # Let the session manager handle the transaction
            await session.flush()

    async def get_by_jira_project_id(self, session: AsyncSession, jira_project_id: str) -> Optional[JiraProjectModel]:
        """Get project by Jira project ID"""
        result = await session.exec(
            select(JiraProjectEntity).where(col(JiraProjectEntity.jira_project_id) == jira_project_id)
        )
        project = result.first()
        return self._to_domain(project) if project else None

    async def get_projects_by_user_id(self, session: AsyncSession, user_id: int) -> List[JiraProjectModel]:
        """Get all projects for a specific user"""
        result = await session.exec(
            select(JiraProjectEntity).where(
                col(JiraProjectEntity.user_id) == user_id
            )
        )
        projects = result.all()
        return [self._to_domain(project) for project in projects]
