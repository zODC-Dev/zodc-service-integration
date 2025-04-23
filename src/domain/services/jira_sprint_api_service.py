from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.domain.models.jira_board import JiraBoardModel
from src.domain.models.jira_sprint import JiraSprintModel


class IJiraSprintAPIService(ABC):
    @abstractmethod
    async def get_sprint_by_id(self, user_id: int, sprint_id: int) -> Optional[JiraSprintModel]:
        """Get sprint by ID"""
        pass

    @abstractmethod
    async def get_sprint_by_id_with_admin_auth(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """Get sprint by ID using admin auth"""
        pass

    @abstractmethod
    async def get_project_sprints(self, user_id: int, project_key: str) -> List[JiraSprintModel]:
        """Get all sprints in a project"""
        pass

    @abstractmethod
    async def get_board_by_id(self, board_id: int) -> Optional[JiraBoardModel]:
        """Get board by ID"""
        pass

    @abstractmethod
    async def start_sprint(self, sprint_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None, goal: Optional[str] = None) -> Optional[JiraSprintModel]:
        """Start a sprint in Jira"""
        pass

    @abstractmethod
    async def end_sprint(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """End a sprint in Jira"""
        pass

    @abstractmethod
    async def create_sprint(self, name: str, board_id: int, project_key: str) -> int:
        """Create a new sprint in Jira

        Returns:
            int: The Jira sprint ID of the created sprint
        """
        pass
