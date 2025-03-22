from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.exceptions.project_exceptions import ProjectNotFoundError
from src.domain.models.jira_project import JiraProjectCreateDTO, JiraProjectModel, JiraProjectUpdateDTO
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.infrastructure.entities.jira_project import JiraProjectEntity


class SQLAlchemyJiraProjectRepository(IJiraProjectRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, entity: JiraProjectEntity) -> JiraProjectModel:
        if not entity:
            return None
        model = JiraProjectModel(
            id=entity.id,
            jira_project_id=entity.jira_project_id,
            key=entity.key,
            name=entity.name,
            description=entity.description,
            avatar_url=entity.avatar_url
        )
        return model

    async def create_project(self, project_data: JiraProjectCreateDTO) -> JiraProjectModel:
        project = JiraProjectEntity(
            jira_project_id=project_data.jira_project_id,
            key=project_data.key,
            name=project_data.name,
            description=project_data.description,
            avatar_url=project_data.avatar_url
        )
        self.session.add(project)
        await self.session.flush()
        return self._to_domain(project)

    async def get_project_by_id(self, project_id: int) -> Optional[JiraProjectModel]:
        project = await self.session.get(JiraProjectEntity, project_id)
        return self._to_domain(project) if project else None

    async def get_project_by_key(self, key: str) -> Optional[JiraProjectModel]:
        result = await self.session.exec(
            select(JiraProjectEntity).where(JiraProjectEntity.key ==
                                            key.upper())
        )
        project = result.first()
        return self._to_domain(project) if project else None

    async def get_all_projects(self) -> List[JiraProjectModel]:
        result = await self.session.exec(select(JiraProjectEntity))
        projects = result.all()
        return [self._to_domain(p) for p in projects]

    async def update_project(self, project_id: int, project_data: JiraProjectUpdateDTO) -> JiraProjectModel:
        project = await self.session.get(JiraProjectEntity, project_id)
        if project:
            if project_data.name is not None:
                project.name = project_data.name
            if project_data.key is not None:
                project.key = project_data.key
            if project_data.description is not None:
                project.description = project_data.description
            await self.session.commit()
            await self.session.refresh(project)
            return self._to_domain(project)
        else:
            raise ProjectNotFoundError(
                f"Project with id {project_id} not found")

    async def delete_project(self, project_id: int) -> None:
        project = await self.session.get(JiraProjectEntity, project_id)
        if project:
            await self.session.delete(project)
            await self.session.commit()

    async def get_by_jira_project_id(self, jira_project_id: str) -> Optional[JiraProjectModel]:
        """Get project by Jira project ID"""
        result = await self.session.exec(
            select(JiraProjectEntity).where(JiraProjectEntity.jira_project_id == jira_project_id)
        )
        project = result.first()
        return self._to_domain(project) if project else None

    async def get_projects_by_user_id(self, user_id: int) -> List[JiraProjectModel]:
        """Get all projects for a specific user"""
        result = await self.session.exec(
            select(JiraProjectEntity).where(
                JiraProjectEntity.user_id == user_id
            )
        )
        projects = result.all()
        return [self._to_domain(project) for project in projects]
