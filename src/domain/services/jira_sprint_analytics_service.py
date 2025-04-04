from abc import ABC, abstractmethod

from src.domain.models.jira_sprint_analytics import SprintBurndownModel, SprintBurnupModel


class IJiraSprintAnalyticsService(ABC):
    """Interface cho Sprint Analytics Service trong domain layer"""

    @abstractmethod
    async def get_sprint_burndown_data(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurndownModel:
        """Lấy dữ liệu burndown chart cho một sprint"""
        pass

    @abstractmethod
    async def get_sprint_burnup_data(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurnupModel:
        """Lấy dữ liệu burnup chart cho một sprint"""
        pass
