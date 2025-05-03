from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class UserPerformanceSummaryModel(BaseModel):
    """Model cho thông tin hiệu suất của người dùng trong một quý"""
    user_id: int
    user_name: str
    quarter: int
    year: int

    # Chỉ số cơ bản
    total_tasks: int
    completed_tasks: int
    task_completion_rate: float  # Tỷ lệ hoàn thành task (%)

    # Chỉ số story points
    total_story_points: float
    completed_story_points: float
    story_point_completion_rate: float  # Tỷ lệ hoàn thành story points (%)

    # Chỉ số thời gian
    average_completion_time: float  # Thời gian hoàn thành trung bình (giờ)
    on_time_completion_rate: float  # Tỷ lệ hoàn thành đúng hạn (%)

    # Chỉ số chất lượng
    bug_fix_rate: float  # Tỷ lệ sửa bug thành công (%)
    rework_rate: float  # Tỷ lệ phải làm lại (%)

    # Chỉ số phân loại task
    task_by_type: Dict[str, int]  # Số lượng task theo loại
    task_by_priority: Dict[str, int]  # Số lượng task theo độ ưu tiên

    # Chỉ số so sánh với team
    team_rank: Optional[int] = None  # Xếp hạng trong team (nếu có)
    team_average_completion_rate: Optional[float] = None  # Tỷ lệ hoàn thành trung bình của team

    # Thông tin chi tiết
    sprint_performance: List[Dict[str, Any]] = []  # Hiệu suất theo từng sprint
    monthly_performance: List[Dict[str, Any]] = []  # Hiệu suất theo từng tháng

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
