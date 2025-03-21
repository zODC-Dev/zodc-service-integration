from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.jira_project import JiraProjectCreateDTO, JiraProjectModel, JiraProjectUpdateDTO


class IJiraProjectRepository(ABC):
    @abstractmethod
    async def create_project(self, project_data: JiraProjectCreateDTO) -> JiraProjectModel:
        pass

    @abstractmethod
    async def get_project_by_id(self, project_id: int) -> Optional[JiraProjectModel]:
        pass

    @abstractmethod
    async def get_project_by_key(self, key: str) -> Optional[JiraProjectModel]:
        pass

    @abstractmethod
    async def get_all_projects(self) -> List[JiraProjectModel]:
        pass

    @abstractmethod
    async def update_project(self, project_id: int, project_data: JiraProjectUpdateDTO) -> JiraProjectModel:
        pass

    @abstractmethod
    async def delete_project(self, project_id: int) -> None:
        pass

    @abstractmethod
    async def get_by_jira_project_id(self, jira_project_id: str) -> Optional[JiraProjectModel]:
        """Get project by Jira project ID"""
        pass
