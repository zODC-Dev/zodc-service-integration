from typing import List, Optional

from pydantic import BaseModel

from src.domain.models.gantt_chart import GanttChartConnectionModel, GanttChartJiraIssueModel, ProjectConfigModel


class GanttChartCalculationRequest(BaseModel):
    """Request model for Gantt chart calculation"""
    transaction_id: Optional[str] = None
    project_key: str
    sprint_id: int
    workflow_id: Optional[int] = None
    config: Optional[ProjectConfigModel] = None
    # Optional fields, can be empty if we want to use data from database
    issues: Optional[List[GanttChartJiraIssueModel]] = None
    connections: Optional[List[GanttChartConnectionModel]] = None
