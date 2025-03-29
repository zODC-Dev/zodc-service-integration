from datetime import datetime, timedelta
from typing import List, Optional

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_sprint_analytics import (
    DailySprintData,
    SprintAnalyticsBaseModel,
    SprintBurndownModel,
    SprintBurnupModel,
)
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_sprint_analytics_service import IJiraSprintAnalyticsService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class JiraSprintAnalyticsService(IJiraSprintAnalyticsService):
    """Service xử lý dữ liệu phân tích sprint cho các loại biểu đồ"""

    def __init__(
        self,
        jira_project_api_service: IJiraProjectAPIService,
        jira_issue_db_service: IJiraIssueDatabaseService,
        jira_sprint_db_service: IJiraSprintDatabaseService
    ):
        self.jira_project_api_service = jira_project_api_service
        self.jira_issue_db_service = jira_issue_db_service
        self.jira_sprint_db_service = jira_sprint_db_service

    async def get_sprint_burndown_data(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurndownModel:
        """Lấy dữ liệu burndown chart cho một sprint"""
        # Lấy thông tin sprint
        sprint = await self._get_sprint_details(sprint_id)
        if not sprint:
            log.error(f"Không tìm thấy sprint {sprint_id}")
            raise ValueError(f"Sprint {sprint_id} not found")

        # Lấy danh sách issues trong sprint
        issues = await self._get_sprint_issues(user_id, project_key, sprint_id)

        # Tính toán dữ liệu burndown
        base_model = await self._calculate_sprint_analytics(sprint, issues, project_key)

        # Chuyển đổi sang model burndown
        return SprintBurndownModel(
            id=sprint.id,
            name=sprint.name,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            project_key=project_key,
            total_points_initial=base_model.total_points_initial,
            total_points_current=base_model.total_points_current,
            daily_data=base_model.daily_data,
            scope_changes=base_model.scope_changes
        )

    async def get_sprint_burnup_data(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurnupModel:
        """Lấy dữ liệu burnup chart cho một sprint"""
        # Lấy thông tin sprint
        sprint = await self._get_sprint_details(sprint_id)
        if not sprint:
            log.error(f"Không tìm thấy sprint {sprint_id}")
            raise ValueError(f"Sprint {sprint_id} not found")

        # Lấy danh sách issues trong sprint
        issues = await self._get_sprint_issues(user_id, project_key, sprint_id)

        # Tính toán dữ liệu
        base_model = await self._calculate_sprint_analytics(sprint, issues, project_key)

        # Chuyển đổi sang model burnup
        return SprintBurnupModel(
            id=sprint.id,
            name=sprint.name,
            start_date=sprint.start_date,
            end_date=sprint.end_date,
            project_key=project_key,
            total_points_initial=base_model.total_points_initial,
            total_points_current=base_model.total_points_current,
            daily_data=base_model.daily_data,
            scope_changes=base_model.scope_changes
        )

    async def _get_sprint_details(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """Lấy thông tin chi tiết của sprint"""
        return await self.jira_sprint_db_service.get_sprint_by_jira_sprint_id(sprint_id)

    async def _get_sprint_issues(self, user_id: int, project_key: str, sprint_id: int) -> List[JiraIssueModel]:
        """Lấy danh sách issues trong sprint"""
        # Sử dụng service có sẵn để lấy issues từ database
        return await self.jira_issue_db_service.get_project_issues(
            user_id=user_id,
            project_key=project_key,
            sprint_id=sprint_id
        )

    async def _calculate_sprint_analytics(
        self,
        sprint: JiraSprintModel,
        issues: List[JiraIssueModel],
        project_key: str
    ) -> SprintAnalyticsBaseModel:
        """Tính toán dữ liệu phân tích sprint dựa trên issues"""
        # Lấy khoảng thời gian của sprint
        start_date = sprint.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = sprint.end_date.replace(hour=23, minute=59, second=59,
                                           microsecond=0) if sprint.end_date else datetime.now() + timedelta(days=14)

        # Tính tổng điểm ban đầu
        total_points_initial = sum(issue.estimate_point or 0 for issue in issues)
        # Tổng điểm hiện tại (có thể thay đổi do scope changes)
        total_points_current = total_points_initial

        # Danh sách các ngày trong sprint
        days = []
        current_date = start_date
        while current_date <= end_date:
            days.append(current_date)
            current_date += timedelta(days=1)

        # Tính toán dữ liệu hàng ngày cho sprint
        daily_data = []
        for i, day in enumerate(days):
            # Tính ideal burndown theo tỷ lệ thời gian
            progress_ratio = i / max(len(days) - 1, 1)  # Tránh chia cho 0
            ideal_remaining = total_points_initial * (1 - progress_ratio)

            # Giả định: trong thực tế cần lấy trạng thái issue vào thời điểm ngày đó
            # Ở đây đơn giản hóa bằng cách sử dụng trạng thái hiện tại
            completed_points = sum(
                (issue.estimate_point or 0)
                for issue in issues
                if issue.status == JiraIssueStatus.DONE
            )

            remaining_points = total_points_current - completed_points

            # Tạo daily data
            daily_data.append(DailySprintData(
                date=day,
                remaining_points=remaining_points,
                completed_points=completed_points,
                ideal_points=ideal_remaining,
                added_points=0  # Mặc định là 0, sẽ cập nhật nếu có scope changes
            ))

        # Giả định: Trong thực tế cần truy vấn lịch sử thay đổi của issues để xác định scope changes
        # Ở đây đơn giản hóa bằng cách giả định không có scope changes
        scope_changes = []

        return SprintAnalyticsBaseModel(
            id=sprint.id,
            name=sprint.name,
            start_date=start_date,
            end_date=end_date,
            project_key=project_key,
            total_points_initial=total_points_initial,
            total_points_current=total_points_current,
            daily_data=daily_data,
            scope_changes=scope_changes
        )
