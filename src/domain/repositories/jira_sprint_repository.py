from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.jira_sprint import JiraSprintCreateDTO, JiraSprintModel, JiraSprintUpdateDTO


class IJiraSprintRepository(ABC):
    @abstractmethod
    async def create_sprint(self, sprint_data: JiraSprintCreateDTO) -> JiraSprintModel:
        pass

    @abstractmethod
    async def update_sprint(self, sprint_id: str, sprint_data: JiraSprintUpdateDTO) -> JiraSprintModel:
        pass

    @abstractmethod
    async def get_sprint_by_id(self, sprint_id: str) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_by_jira_sprint_id(self, jira_sprint_id: str) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_project_sprints(self, project_key: str) -> List[JiraSprintModel]:
        """Get all sprints for a specific project"""
        pass
