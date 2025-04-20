from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel

from src.app.schemas.responses.base import BaseResponse
from src.domain.models.apis.jira_user import JiraAssigneeResponse


class ScopeChangeResponse(BaseModel):
    """Schema for scope change data"""
    date: str
    points_added: float = Field(..., alias="pointsAdded")
    issue_keys: List[str] = Field(..., alias="issueKeys")

    class Config:
        populate_by_name = True


class BaseSprintAnalyticsResponse(BaseResponse):
    """Base response schema cho các loại Sprint Analytics"""
    sprint_name: str = Field(..., alias="sprintName")
    start_date: str = Field(..., alias="startDate")
    end_date: str = Field(..., alias="endDate")

    total_points_initial: float = Field(..., alias="totalPointsInitial")
    total_points_current: float = Field(..., alias="totalPointsCurrent")

    dates: List[str]
    added_points: List[float] = Field(..., alias="addedPoints")

    scope_changes: Optional[List[ScopeChangeResponse]] = Field(None, alias="scopeChanges")

    class Config:
        populate_by_name = True


class SprintBurndownResponse(BaseSprintAnalyticsResponse):
    """Response schema cho Burndown Chart API"""
    ideal_burndown: List[float] = Field(..., alias="idealBurndown")
    actual_burndown: List[float | None] = Field(..., alias="actualBurndown")

    class Config:
        populate_by_name = True


class SprintBurnupResponse(BaseSprintAnalyticsResponse):
    """Response schema cho Burnup Chart API"""
    ideal_burnup: List[float] = Field(..., alias="idealBurnup")
    actual_burnup: List[float | None] = Field(..., alias="actualBurnup")
    scope_line: List[float] = Field(..., alias="scopeLine")

    class Config:
        populate_by_name = True


class TaskReportResponse(BaseModel):
    """Response schema for task report data"""
    number_of_tasks: int
    percentage: float
    points: float

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class SprintGoalResponse(BaseResponse):
    """Response schema for sprint goal data"""
    id: str
    goal: str
    completed_tasks: TaskReportResponse
    in_progress_tasks: TaskReportResponse
    to_do_tasks: TaskReportResponse
    added_points: float
    total_points: float

    class Config:
        populate_by_name = True


class BugPriorityCountResponse(BaseModel):
    """Response schema for bug priority count data"""
    lowest: int
    low: int
    medium: int
    high: int
    highest: int

    class Config:
        populate_by_name = True


class BugChartResponse(BaseModel):
    """Response schema for bug chart data"""
    priority: BugPriorityCountResponse
    total: int

    class Config:
        populate_by_name = True


class BugTaskResponse(BaseModel):
    """Response schema for bug task data"""
    id: str
    key: str
    link: str
    summary: str
    points: float
    priority: str
    status: str
    assignee: Optional[JiraAssigneeResponse] = None
    created_at: str
    updated_at: str

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class BugReportDataResponse(BaseResponse):
    """Response schema for bug report data"""
    bugs: List[BugTaskResponse]
    bugs_chart: List[BugChartResponse] = Field(..., alias="bugsChart")

    class Config:
        populate_by_name = True


class WorkloadResponse(BaseModel):
    """DTO for team member workload data in API response"""
    user_name: str = Field(alias="userName")
    completed_points: float = Field(alias="completedPoints")
    remaining_points: float = Field(alias="remainingPoints")

    class Config:
        populate_by_name = True
