from abc import ABC, abstractmethod
from typing import List

from src.domain.models.gantt_chart import GanttChartConnectionModel, GanttChartJiraIssueModel


class IWorkflowServiceClient(ABC):
    """Interface for workflow service client"""

    @abstractmethod
    async def get_workflow_connections(
        self,
        workflow_id: str
    ) -> List[GanttChartConnectionModel]:
        """Get connections for a workflow"""
        pass

    @abstractmethod
    async def get_workflow_issues(
        self,
        workflow_id: str
    ) -> List[GanttChartJiraIssueModel]:
        """Get issues for a workflow"""
        pass
