from abc import ABC, abstractmethod
from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.database.jira_project import JiraProjectDBCreateDTO, JiraProjectDBUpdateDTO
from src.domain.models.jira_project import JiraProjectModel


class IJiraProjectRepository(ABC):
    @abstractmethod
    async def create_project(self, session: AsyncSession, project_data: JiraProjectDBCreateDTO) -> JiraProjectModel:
        pass

    @abstractmethod
    async def get_project_by_id(self, session: AsyncSession, project_id: int) -> Optional[JiraProjectModel]:
        pass

    @abstractmethod
    async def get_project_by_key(self, session: AsyncSession, key: str) -> Optional[JiraProjectModel]:
        pass

    @abstractmethod
    async def get_all_projects(self, session: AsyncSession) -> List[JiraProjectModel]:
        pass

    @abstractmethod
    async def update_project(self, session: AsyncSession, project_id: int, project_data: JiraProjectDBUpdateDTO) -> JiraProjectModel:
        pass

    @abstractmethod
    async def delete_project(self, session: AsyncSession, project_id: int) -> None:
        pass

    @abstractmethod
    async def get_by_jira_project_id(self, session: AsyncSession, jira_project_id: str) -> Optional[JiraProjectModel]:
        """Get project by Jira project ID"""
        pass

    @abstractmethod
    async def get_projects_by_user_id(self, session: AsyncSession, user_id: int) -> List[JiraProjectModel]:
        """Get all projects for a specific user"""
        pass
