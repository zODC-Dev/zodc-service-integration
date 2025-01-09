from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.jira import JiraTask


class IJiraService(ABC):
    @abstractmethod
    async def get_project_tasks(
        self,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraTask]:
        """Get tasks from a specific Jira project"""
        pass
