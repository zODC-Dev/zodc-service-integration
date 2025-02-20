from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.project import Project, ProjectCreate, ProjectUpdate


class IProjectRepository(ABC):
    @abstractmethod
    async def create_project(self, project_data: ProjectCreate) -> Project:
        pass

    @abstractmethod
    async def get_project_by_id(self, project_id: int) -> Optional[Project]:
        pass

    @abstractmethod
    async def get_project_by_key(self, key: str) -> Optional[Project]:
        pass

    @abstractmethod
    async def get_all_projects(self) -> List[Project]:
        pass

    @abstractmethod
    async def update_project(self, project_id: int, project_data: ProjectUpdate) -> Project:
        pass

    @abstractmethod
    async def delete_project(self, project_id: int) -> None:
        pass

    @abstractmethod
    async def get_user_projects(self, user_id: int) -> List[Project]:
        pass
