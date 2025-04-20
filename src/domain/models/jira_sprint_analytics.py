from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from src.domain.constants.jira import JiraIssueStatus
from src.domain.models.apis.jira_user import JiraAssigneeResponse


class SprintAnalyticsType(str, Enum):
    """Các loại biểu đồ sprint analytics"""
    BURNDOWN = "burndown"
    BURNUP = "burnup"


class SprintScopeChange(BaseModel):
    """Model cho thay đổi phạm vi của sprint"""
    date: datetime
    points_added: float
    issue_keys: List[str]


class DailySprintData(BaseModel):
    """Dữ liệu hàng ngày của một sprint"""
    date: datetime
    remaining_points: float
    completed_points: float
    ideal_points: float
    added_points: float = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for API response"""
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "remainingPoints": self.remaining_points,
            "completedPoints": self.completed_points,
            "idealPoints": self.ideal_points,
            "addedPoints": self.added_points
        }


class SprintAnalyticsBaseModel(BaseModel):
    """Base model cho tất cả các loại analytics của sprint"""
    id: int
    name: str
    start_date: datetime
    end_date: datetime
    project_key: str

    # Thông tin cơ bản
    total_points_initial: float = 0
    total_points_current: float = 0

    # Timeline data
    daily_data: List[DailySprintData] = []

    # Thông tin thay đổi phạm vi
    scope_changes: List[SprintScopeChange] = []

    def get_dates_list(self) -> List[str]:
        """Lấy danh sách các ngày trong sprint theo định dạng yyyy-MM-dd"""
        return [data.date.strftime("%Y-%m-%d") for data in self.daily_data]

    def get_ideal_burndown(self) -> List[float]:
        """Lấy danh sách các điểm theo đường burndown lý tưởng"""
        return [data.ideal_points for data in self.daily_data]

    def get_actual_burndown(self) -> List[float]:
        """Lấy danh sách các điểm burndown thực tế"""
        return [data.remaining_points for data in self.daily_data]

    def get_added_points(self) -> List[float]:
        """Lấy danh sách các điểm được thêm vào mỗi ngày"""
        return [data.added_points for data in self.daily_data]


class SprintBurndownModel(SprintAnalyticsBaseModel):
    """Model cho dữ liệu burndown chart của một sprint"""
    pass


class SprintBurnupModel(SprintAnalyticsBaseModel):
    """Model cho dữ liệu burnup chart của một sprint"""

    def get_actual_burnup(self) -> List[float]:
        """Lấy danh sách các điểm burnup thực tế"""
        return [data.completed_points for data in self.daily_data]

    def get_scope_line(self) -> List[float]:
        """Lấy scope line cho burnup chart (tổng số điểm theo thời gian)"""
        return [data.completed_points + data.remaining_points for data in self.daily_data]


class TaskReportModel(BaseModel):
    """Model for task report data"""
    number_of_tasks: int
    percentage: float
    points: float


class SprintGoalModel(BaseModel):
    """Model for sprint goal data"""
    id: str
    goal: str
    completed_tasks: TaskReportModel
    in_progress_tasks: TaskReportModel
    to_do_tasks: TaskReportModel
    added_points: float
    total_points: float


class BugPriorityCountModel(BaseModel):
    """Model for bug priority count data"""
    lowest: int
    low: int
    medium: int
    high: int
    highest: int


class BugChartModel(BaseModel):
    """Model for bug chart data"""
    priority: BugPriorityCountModel
    total: int


class BugTaskModel(BaseModel):
    """Model for bug task data"""
    id: str
    key: str
    link: str
    summary: str
    points: float
    priority: str
    status: JiraIssueStatus
    assignee: Optional[JiraAssigneeResponse] = None
    created_at: datetime
    updated_at: datetime


class BugReportDataModel(BaseModel):
    """Model for bug report data"""
    bugs: List[BugTaskModel]
    bugs_chart: List[BugChartModel]


class WorkloadModel(BaseModel):
    """Model for team member workload data"""
    user_name: str
    completed_points: float
    remaining_points: float
