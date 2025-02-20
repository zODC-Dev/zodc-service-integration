from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.entities.project import Project as ProjectEntity, ProjectCreate, ProjectUpdate
from src.domain.exceptions.project_exceptions import ProjectNotFoundError
from src.domain.repositories.project_repository import IProjectRepository
from src.infrastructure.models.project import Project, UserProjectRole


class SQLAlchemyProjectRepository(IProjectRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_project(self, project_data: ProjectCreate) -> ProjectEntity:
        project = Project(
            name=project_data.name,
            key=project_data.key,
            description=project_data.description
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

    async def get_user_projects(self, user_id: int) -> List[ProjectEntity]:
        result = await self.session.exec(
            select(Project)
            .join(UserProjectRole)
            .where(UserProjectRole.user_id == user_id)
            .distinct()
        )
        projects = result.all()
        return [self._to_domain(p) for p in projects]

    def _to_domain(self, project: Project) -> ProjectEntity:
        return ProjectEntity(
            id=project.id,
            name=project.name,
            key=project.key,
            description=project.description,
            user_project_roles=[]
        )
