from abc import ABC, abstractmethod
from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.database.jira_sprint import JiraSprintDBCreateDTO, JiraSprintDBUpdateDTO
from src.domain.models.jira_sprint import JiraSprintModel


class IJiraSprintRepository(ABC):
    @abstractmethod
    async def create_sprint(self, session: AsyncSession, sprint_data: JiraSprintDBCreateDTO) -> JiraSprintModel:
        pass

    @abstractmethod
    async def update_sprint(self, session: AsyncSession, sprint_id: int, sprint_data: JiraSprintDBUpdateDTO) -> JiraSprintModel:
        pass

    @abstractmethod
    async def get_sprint_by_id(self, session: AsyncSession, sprint_id: int, include_deleted: bool = False) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_sprint_by_jira_sprint_id(self, session: AsyncSession, jira_sprint_id: int, include_deleted: bool = False) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_current_sprint(self, session: AsyncSession, project_key: str) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_sprints_by_project_key(self, session: AsyncSession, project_key: str, include_deleted: bool = False) -> List[JiraSprintModel]:
        """Get all sprints for a project"""
        pass

    @abstractmethod
    async def get_project_sprints(self, session: AsyncSession, project_key: str, include_deleted: bool = False) -> List[JiraSprintModel]:
        """Get all sprints for a specific project"""
        pass

    @abstractmethod
    async def update_sprint_by_jira_sprint_id(self, session: AsyncSession, jira_sprint_id: int, sprint_data: JiraSprintDBUpdateDTO) -> JiraSprintModel:
        pass

    @abstractmethod
    async def get_all_sprints(self, session: AsyncSession) -> List[JiraSprintModel]:
        pass
