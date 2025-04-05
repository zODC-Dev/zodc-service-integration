from datetime import datetime, time
from typing import List, Optional

from pydantic import BaseModel


class ScheduleConfigModel(BaseModel):
    """Configuration for schedule calculation"""
    working_hours_per_day: int = 8
    hours_per_point: int = 4
    start_work_hour: time = time(9, 0)
    end_work_hour: time = time(17, 30)
    lunch_break_minutes: int = 30
    include_weekends: bool = False


class TaskScheduleModel(BaseModel):
    """Model for a scheduled task in a Gantt chart"""
    node_id: str
    jira_key: Optional[str] = None
    title: str
    type: str  # Task, Story, Bug, etc.
    estimate_points: float = 0
    estimate_hours: float = 0
    plan_start_time: datetime
    plan_end_time: datetime
    predecessors: List[str] = []
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None

    class Config:
        from_attributes = True


class GanttChartModel(BaseModel):
    """Model for a Gantt chart"""
    sprint_id: int
    sprint_name: Optional[str] = None
    project_key: str
    tasks: List[TaskScheduleModel]
    start_date: datetime
    end_date: datetime
    is_feasible: bool = True  # True if all tasks can be completed within sprint duration
    config: ScheduleConfigModel

    class Config:
        from_attributes = True


class GanttChartJiraIssueModel(BaseModel):
    """Model for a Jira issue in calculation input"""
    node_id: str
    jira_key: Optional[str] = None
    title: str
    type: str
    estimate_points: float = 0
    assignee_id: Optional[str] = None


class GanttChartConnectionModel(BaseModel):
    """Model for a connection between issues"""
    from_issue_key: str
    to_issue_key: str
    type: str = "relates to"
