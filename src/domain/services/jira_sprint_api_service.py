from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.jira_board import JiraBoardModel
from src.domain.models.jira_sprint import JiraSprintModel


class IJiraSprintAPIService(ABC):
    @abstractmethod
    async def get_project_sprints(self, user_id: int, project_key: str) -> List[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_sprint_by_id(self, user_id: int, sprint_id: int) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_sprint_by_id_with_system_user(self, sprint_id: int) -> Optional[JiraSprintModel]:
        pass

    @abstractmethod
    async def get_board_by_id(self, board_id: int) -> Optional[JiraBoardModel]:
        """Get board information by ID"""
        pass
