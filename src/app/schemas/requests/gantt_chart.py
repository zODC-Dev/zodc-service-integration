from typing import Optional

from pydantic import BaseModel, Field


class GanttChartRequest(BaseModel):
    """Request schema for Gantt chart operations"""
    working_hours_per_day: int = Field(default=8, gt=0, le=24, description="Working hours per day")
    hours_per_point: int = Field(default=4, gt=0, le=40, description="Hours per story point")
    include_weekends: bool = Field(default=False, description="Whether to include weekends in schedule")
    lunch_break_minutes: int = Field(default=30, ge=0, le=120, description="Lunch break duration in minutes")
    workflow_id: Optional[str] = Field(default=None, description="Specific workflow ID to get connections from")
