from abc import ABC, abstractmethod
from typing import List

from src.domain.models.jira_project import JiraProjectModel, JiraSprintModel


class IJiraProjectAPIService(ABC):
    @abstractmethod
    async def get_accessible_projects(self, user_id: int) -> List[JiraProjectModel]:
        """Get all accessible Jira projects from API"""
        pass

    @abstractmethod
    async def get_project_sprints(
        self,
        user_id: int,
        project_id: str
    ) -> List[JiraSprintModel]:
        """Get all sprints in a project from API"""
        pass
