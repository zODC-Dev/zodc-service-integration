from abc import ABC, abstractmethod
from typing import List

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.jira_sprint_analytics import (
    BugReportDataModel,
    SprintBurndownModel,
    SprintBurnupModel,
    SprintGoalModel,
    WorkloadModel,
)


class IJiraSprintAnalyticsService(ABC):
    """Interface cho Sprint Analytics Service trong domain layer"""

    @abstractmethod
    async def get_sprint_burndown_data(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurndownModel:
        """Lấy dữ liệu burndown chart cho một sprint"""
        pass

    @abstractmethod
    async def get_sprint_burnup_data(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurnupModel:
        """Lấy dữ liệu burnup chart cho một sprint"""
        pass

    @abstractmethod
    async def get_sprint_goal_data(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintGoalModel:
        """Lấy dữ liệu sprint goal cho một sprint"""
        pass

    @abstractmethod
    async def get_bug_report_data(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> BugReportDataModel:
        """Lấy dữ liệu báo cáo bug cho một sprint"""
        pass

    @abstractmethod
    async def get_team_workload_data(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> List[WorkloadModel]:
        """Lấy dữ liệu workload của các thành viên trong sprint"""
        pass
