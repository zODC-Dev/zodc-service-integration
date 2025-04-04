from typing import List, Optional

from pydantic import BaseModel, Field

from src.app.schemas.responses.base import BaseResponse


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
    actual_burndown: List[float] = Field(..., alias="actualBurndown")

    class Config:
        populate_by_name = True


class SprintBurnupResponse(BaseSprintAnalyticsResponse):
    """Response schema cho Burnup Chart API"""
    ideal_burnup: List[float] = Field(..., alias="idealBurnup")
    actual_burnup: List[float] = Field(..., alias="actualBurnup")
    scope_line: List[float] = Field(..., alias="scopeLine")

    class Config:
        populate_by_name = True
