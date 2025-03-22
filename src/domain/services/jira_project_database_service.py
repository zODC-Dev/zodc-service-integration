from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.jira_project import JiraProjectCreateDTO, JiraProjectModel, JiraProjectUpdateDTO


class IJiraProjectDatabaseService(ABC):
    @abstractmethod
    async def get_project(self, project_id: int) -> Optional[JiraProjectModel]:
        pass

    @abstractmethod
    async def get_project_by_key(self, key: str) -> Optional[JiraProjectModel]:
        pass

    @abstractmethod
    async def get_all_projects(self) -> List[JiraProjectModel]:
        pass

    @abstractmethod
    async def create_project(self, project_data: JiraProjectCreateDTO) -> JiraProjectModel:
        pass

    @abstractmethod
    async def update_project(
        self,
        project_id: int,
        project_data: JiraProjectUpdateDTO
    ) -> JiraProjectModel:
        pass

    @abstractmethod
    async def delete_project(self, project_id: int) -> None:
        pass

    @abstractmethod
    async def get_user_projects(self, user_id: int) -> List[JiraProjectModel]:
        pass
