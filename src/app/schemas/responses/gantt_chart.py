from datetime import datetime
from typing import Optional


from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel

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

    class Config:
        populate_by_name = True
        alias_generator = to_camel
