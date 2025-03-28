from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.database.jira_sprint import JiraSprintDBCreateDTO, JiraSprintDBUpdateDTO
from src.domain.models.jira_sprint import JiraSprintModel


class IJiraSprintRepository(ABC):
    @abstractmethod
    async def create_sprint(self, sprint_data: JiraSprintDBCreateDTO) -> JiraSprintModel:
        pass

    @abstractmethod
    async def update_sprint(self, sprint_id: int, sprint_data: JiraSprintDBUpdateDTO) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_sprint_by_id(self, sprint_id: int) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_sprint_by_jira_sprint_id(self, jira_sprint_id: int) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_current_sprint(self, project_key: str) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_project_sprints(self, project_key: str) -> List[JiraSprintModel]:
        """Get all sprints for a specific project"""
        pass

    @abstractmethod
    async def update_sprint_by_jira_sprint_id(self, jira_sprint_id: int, sprint_data: JiraSprintDBUpdateDTO) -> Optional[JiraSprintModel]:
        pass
