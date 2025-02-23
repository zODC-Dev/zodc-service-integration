from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.entities.project import Project as ProjectEntity, ProjectCreate, ProjectUpdate
from src.domain.exceptions.project_exceptions import ProjectNotFoundError
from src.domain.repositories.project_repository import IProjectRepository
from src.infrastructure.models.project import Project


class SQLAlchemyProjectRepository(IProjectRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_project(self, project_data: ProjectCreate) -> ProjectEntity:
        project = Project(
            project_id=project_data.project_id,
            name=project_data.name,
            key=project_data.key,
            jira_project_id=project_data.jira_project_id,
            avatar_url=project_data.avatar_url,
            is_linked=project_data.is_linked
        )
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return self._to_domain(project)

    async def get_project_by_id(self, project_id: int) -> Optional[ProjectEntity]:
        project = await self.session.get(Project, project_id)
        return self._to_domain(project) if project else None

    async def get_project_by_key(self, key: str) -> Optional[ProjectEntity]:
        result = await self.session.exec(
            select(Project).where(Project.key ==
                                  key.upper())
        )
        project = result.first()
        return self._to_domain(project) if project else None

    async def get_all_projects(self) -> List[ProjectEntity]:
        result = await self.session.exec(select(Project))
        projects = result.all()
        return [self._to_domain(p) for p in projects]

    async def update_project(self, project_id: int, project_data: ProjectUpdate) -> ProjectEntity:
        project = await self.session.get(Project, project_id)
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
        project = await self.session.get(Project, project_id)
        if project:
            await self.session.delete(project)
            await self.session.commit()

    async def get_by_jira_project_id(self, jira_project_id: str) -> Optional[ProjectEntity]:
        """Get project by Jira project ID"""
        result = await self.session.exec(
            select(Project).where(Project.jira_project_id == jira_project_id)
        )
        project = result.first()
        return self._to_domain(project) if project else None

    def _to_domain(self, project: Project) -> ProjectEntity:
        return ProjectEntity(
            project_id=project.project_id,
            name=project.name,
            key=project.key,
            jira_project_id=project.jira_project_id,
            avatar_url=project.avatar_url,
            is_linked=project.is_linked
        )
