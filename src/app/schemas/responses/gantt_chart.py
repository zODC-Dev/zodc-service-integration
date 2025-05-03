from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from src.domain.constants.jira import JiraIssueStatus, JiraIssueType


class GanttTaskResponse(BaseModel):
    """Response schema for a task in Gantt chart"""
    id: str = Field(..., description="Task ID (jira_key or node_id)")
    name: str = Field(..., description="Task title")
    assignee: Optional[str] = Field(default=None, description="Assignee name")
    type: JiraIssueType = Field(..., description="Task type (Story, Task, Bug)")
    status: JiraIssueStatus = Field(..., description="Task status")
    progress: Optional[float] = Field(default=None, description="Task progress if it's a story")
    dependencies: Optional[str] = Field(default=None, description="Story ID that this task belongs to")
    plan_start: Optional[datetime] = Field(default=None, description="Planned start time")
    plan_end: Optional[datetime] = Field(default=None, description="Planned end time")
    actual_start: Optional[datetime] = Field(default=None, description="Actual start time")
    actual_end: Optional[datetime] = Field(default=None, description="Actual end time")


class GanttChartFeasibilityResponse(BaseModel):
    """Response schema for sprint feasibility check"""
    is_feasible: bool = Field(..., description="Whether all tasks can be completed within sprint duration")
    total_points: float = Field(..., description="Total story points in sprint")
    total_hours: float = Field(..., description="Total hours in sprint")
    sprint_start_date: datetime = Field(..., description="Sprint start date")
    sprint_end_date: datetime = Field(..., description="Sprint end date")
    expected_completion_date: datetime = Field(..., description="Expected completion date of all tasks")
    task_count: int = Field(..., description="Number of tasks in sprint")
