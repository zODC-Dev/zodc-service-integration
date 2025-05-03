from typing import Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel

from src.app.schemas.responses.base import BaseResponse


class SprintPerformanceResponse(BaseModel):
    """Response schema cho hiệu suất theo sprint"""
    sprint_id: int = Field(..., alias="sprintId")
    sprint_name: str = Field(..., alias="sprintName")
    start_date: str = Field(..., alias="startDate")
    end_date: str = Field(..., alias="endDate")
    completed_tasks: int = Field(..., alias="completedTasks")
    total_tasks: int = Field(..., alias="totalTasks")
    completed_points: float = Field(..., alias="completedPoints")
    total_points: float = Field(..., alias="totalPoints")
    completion_rate: float = Field(..., alias="completionRate")

    class Config:
        populate_by_name = True


class MonthlyPerformanceResponse(BaseModel):
    """Response schema cho hiệu suất theo tháng"""
    month: int
    year: int
    completed_tasks: int = Field(..., alias="completedTasks")
    total_tasks: int = Field(..., alias="totalTasks")
    completed_points: float = Field(..., alias="completedPoints")
    total_points: float = Field(..., alias="totalPoints")
    completion_rate: float = Field(..., alias="completionRate")

    class Config:
        populate_by_name = True


class UserPerformanceSummaryResponse(BaseResponse):
    """Response schema cho thông tin hiệu suất của người dùng"""
    user_id: int = Field(..., alias="userId")
    user_name: str = Field(..., alias="userName")
    user_email: str = Field(..., alias="userEmail")
    quarter: int
    year: int

    avatar_url: str = Field(..., alias="avatarUrl")

    # Chỉ số cơ bản
    total_tasks: int = Field(..., alias="totalTasks")
    completed_tasks: int = Field(..., alias="completedTasks")
    task_completion_rate: float = Field(..., alias="taskCompletionRate")

    # Chỉ số story points
    total_story_points: float = Field(..., alias="totalStoryPoints")
    completed_story_points: float = Field(..., alias="completedStoryPoints")
    story_point_completion_rate: float = Field(..., alias="storyPointCompletionRate")

    # Chỉ số thời gian
    average_completion_time: float = Field(..., alias="averageCompletionTime")
    on_time_completion_rate: float = Field(..., alias="onTimeCompletionRate")

    # Chỉ số chất lượng
    bug_fix_rate: float = Field(..., alias="bugFixRate")
    rework_rate: float = Field(..., alias="reworkRate")

    # Chỉ số phân loại task
    task_by_type: Dict[str, int] = Field(..., alias="taskByType")
    task_by_priority: Dict[str, int] = Field(..., alias="taskByPriority")

    # Chỉ số so sánh với team
    team_rank: Optional[int] = Field(None, alias="teamRank")
    team_average_completion_rate: Optional[float] = Field(None, alias="teamAverageCompletionRate")

    # Thông tin chi tiết
    sprint_performance: List[SprintPerformanceResponse] = Field(..., alias="sprintPerformance")
    monthly_performance: List[MonthlyPerformanceResponse] = Field(..., alias="monthlyPerformance")

    class Config:
        populate_by_name = True
        alias_generator = to_camel
