from abc import ABC, abstractmethod
from typing import List

from src.domain.models.jira_sprint import JiraSprintModel


class IJiraSprintAPIService(ABC):
    @abstractmethod
    async def get_sprint_details(self, user_id: int, sprint_id: str) -> JiraSprintModel:
        pass

    @abstractmethod
    async def get_project_sprints(self, user_id: int, project_key: str) -> List[JiraSprintModel]:
        pass
