from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class GanttChartTaskResponseModel(BaseModel):
    """Response model for a task in Gantt chart calculation"""
    node_id: str
    jira_key: Optional[str] = None
    title: str
    type: str
    estimate_points: float
    estimate_hours: float
    plan_start_time: datetime
    plan_end_time: datetime
    predecessors: List[str] = []
    assignee_id: Optional[str] = None


class GanttChartCalculationReply(BaseModel):
    """Reply model for Gantt chart calculation"""
    transaction_id: str
    project_key: str
    sprint_id: int
    sprint_start_date: datetime
    sprint_end_date: datetime
    tasks: List[GanttChartTaskResponseModel]
    is_feasible: bool
