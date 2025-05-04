from datetime import datetime, time
from typing import List, Optional

from pydantic import BaseModel


class ProjectConfigModel(BaseModel):
    """Configuration for schedule calculation"""
    working_hours_per_day: int = 8
    estimate_point_to_hours: int = 4
    start_work_hour: time = time(9, 0)
    end_work_hour: time = time(17, 30)
    lunch_break_minutes: int = 30
    # include_weekends: bool = False  # Removed as it will never be True


class GanttChartJiraIssueModel(BaseModel):
    """Model for a Jira issue in calculation input"""
    node_id: str
    jira_key: str
    type: str  # TASK, BUG, STORY
    title: Optional[str] = None  # Will be populated from DB if available
    estimate_points: float = 0   # Will be populated from DB if available
    assignee_id: Optional[str] = None


class GanttChartConnectionModel(BaseModel):
    """Model for a connection between issues"""
    from_node_id: str
    to_node_id: str
    type: str  # "contains" or "relates to"


class TaskScheduleModel(BaseModel):
    """Model for a scheduled task in a Gantt chart"""
    node_id: str
    jira_key: Optional[str] = None
    title: str
    type: str  # TASK, STORY, BUG, etc.
    estimate_points: float = 0
    estimate_hours: float = 0
    plan_start_time: datetime
    plan_end_time: datetime
    predecessors: List[str] = []  # Node IDs this task depends on
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    contains: List[str] = []  # For stories: list of contained task node_ids

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
    config: ProjectConfigModel

    class Config:
        from_attributes = True
