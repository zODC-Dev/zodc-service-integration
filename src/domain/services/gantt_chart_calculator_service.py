from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List

from src.domain.models.gantt_chart import (
    GanttChartConnectionModel,
    GanttChartJiraIssueModel,
    ProjectConfigModel,
    TaskScheduleModel,
)


class IGanttChartCalculatorService(ABC):
    """Interface for Gantt chart calculator service"""

    @abstractmethod
    async def calculate_schedule(
        self,
        sprint_start_date: datetime,
        sprint_end_date: datetime,
        issues: List[GanttChartJiraIssueModel],
        connections: List[GanttChartConnectionModel],
        hierarchy_map: Dict[str, List[str]],
        config: ProjectConfigModel
    ) -> List[TaskScheduleModel]:
        """Calculate schedule for tasks based on dependencies and constraints

        Parameters:
        - sprint_start_date: Start date of the sprint
        - sprint_end_date: End date of the sprint
        - issues: List of issues with their details
        - connections: List of connections between issues
        - hierarchy_map: Map of parent-child relationships (parent_id -> List[child_id])
        - config: Schedule configuration

        Returns:
        - List of scheduled tasks with start and end times
        """
        pass

    @abstractmethod
    def is_schedule_feasible(
        self,
        tasks: List[TaskScheduleModel],
        sprint_end_date: datetime
    ) -> bool:
        """Check if the schedule is feasible (all tasks can be completed within sprint duration)

        Parameters:
        - tasks: List of scheduled tasks
        - sprint_end_date: End date of the sprint

        Returns:
        - True if all tasks can be completed within sprint duration, False otherwise
        """
        pass
