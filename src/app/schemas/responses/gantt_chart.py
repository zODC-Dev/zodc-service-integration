from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GanttChartTaskResponse(BaseModel):
    """Response schema for a task in Gantt chart"""
    id: str = Field(..., description="Task ID (jira_key or node_id)")
    text: str = Field(..., description="Task title")
    start_date: datetime = Field(..., description="Planned start time")
    end_date: datetime = Field(..., description="Planned end time")
    progress: float = Field(default=0, description="Task progress (0-1)")
    type: str = Field(..., description="Task type (Story, Task, Bug, etc.)")
    estimate_points: float = Field(..., description="Estimate in story points")
    estimate_hours: float = Field(..., description="Estimate in hours")
    assignee: Optional[str] = Field(default=None, description="Assignee name")
    predecessors: List[str] = Field(default=[], description="Predecessor task IDs")


class GanttChartResponse(BaseModel):
    """Response schema for Gantt chart"""
    project_key: str = Field(..., description="Project key")
    sprint_id: int = Field(..., description="Sprint ID")
    sprint_name: str = Field(..., description="Sprint name")
    sprint_start_date: datetime = Field(..., description="Sprint start date")
    sprint_end_date: datetime = Field(..., description="Sprint end date")
    tasks: List[Dict[str, Any]] = Field(..., description="List of tasks")
    is_feasible: bool = Field(..., description="Whether all tasks can be completed within sprint duration")
    working_hours_per_day: int = Field(..., description="Working hours per day used for calculation")
    hours_per_point: int = Field(..., description="Hours per story point used for calculation")


class GanttChartFeasibilityResponse(BaseModel):
    """Response schema for sprint feasibility check"""
    is_feasible: bool = Field(..., description="Whether all tasks can be completed within sprint duration")
    total_points: float = Field(..., description="Total story points in sprint")
    total_hours: float = Field(..., description="Total hours in sprint")
    sprint_start_date: datetime = Field(..., description="Sprint start date")
    sprint_end_date: datetime = Field(..., description="Sprint end date")
    expected_completion_date: datetime = Field(..., description="Expected completion date of all tasks")
    task_count: int = Field(..., description="Number of tasks in sprint")
