from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_sprint_analytics import (
    DailySprintData,
    SprintAnalyticsBaseModel,
    SprintBurndownModel,
    SprintBurnupModel,
    SprintScopeChange,
)
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_sprint_analytics_service import IJiraSprintAnalyticsService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class JiraSprintAnalyticsService(IJiraSprintAnalyticsService):
    """Service xử lý dữ liệu phân tích sprint cho các loại biểu đồ"""

    def __init__(
        self,
        jira_project_api_service: IJiraProjectAPIService,
        jira_issue_db_service: IJiraIssueDatabaseService,
        jira_sprint_db_service: IJiraSprintDatabaseService,
        jira_issue_history_db_service: IJiraIssueHistoryDatabaseService
    ):
        self.jira_project_api_service = jira_project_api_service
        self.jira_issue_db_service = jira_issue_db_service
        self.jira_sprint_db_service = jira_sprint_db_service
        self.jira_issue_history_db_service = jira_issue_history_db_service

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

        # Tính toán scope changes và tổng điểm hiện tại
        assert sprint.id is not None, "Sprint ID must be provided"
        scope_changes, daily_scope_points = await self._calculate_scope_changes(
            issues, start_date, end_date, sprint.id
        )

        # Tổng điểm hiện tại (có thể thay đổi do scope changes)
        total_points_current = total_points_initial + sum(change.points_added for change in scope_changes)

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

            # Format ngày hiện tại để so sánh với daily_scope_points
            day_str = day.strftime("%Y-%m-%d")

            # Lấy số điểm được thêm vào cho ngày này
            added_points = daily_scope_points.get(day_str, 0)

            # Tính toán điểm hoàn thành dựa trên trạng thái và hạn của issues
            # Filter issues có trong sprint tính đến ngày day
            current_issues = [
                issue for issue in issues
                if self._is_issue_in_sprint_at_date(issue, sprint.id, day)
            ]

            log.info(f"Day: {day}, issues: {len(issues)}, current issues: {len(current_issues)}")

            # Tính completed_points - những issues đã Done tính đến ngày day
            completed_points = sum(
                (issue.estimate_point or 0)
                for issue in current_issues
                if issue.status == JiraIssueStatus.DONE and
                (issue.updated_at is None or issue.updated_at <= day)
            )

            # Tính total points cho đến ngày này
            total_points_day = total_points_initial
            for d in range(i + 1):
                d_str = days[d].strftime("%Y-%m-%d")
                total_points_day += daily_scope_points.get(d_str, 0)

            remaining_points = total_points_day - completed_points

            # Tạo daily data
            daily_data.append(DailySprintData(
                date=day,
                remaining_points=remaining_points,
                completed_points=completed_points,
                ideal_points=ideal_remaining,
                added_points=added_points
            ))

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

    def _is_issue_in_sprint_at_date(self, issue: JiraIssueModel, sprint_id: int, date: datetime) -> bool:
        """Kiểm tra xem issue có thuộc sprint vào một ngày cụ thể không"""
        # Nếu issue không có sprint, return False
        if not issue.sprints:
            return False

        # Kiểm tra nếu issue thuộc sprint và được tạo trước hoặc trong ngày đang xét
        for sprint in issue.sprints:
            if sprint and sprint.jira_sprint_id == sprint_id and issue.created_at <= date:
                return True

        return False

    async def _calculate_scope_changes(
        self,
        issues: List[JiraIssueModel],
        start_date: datetime,
        end_date: datetime,
        sprint_id: int
    ) -> Tuple[List[SprintScopeChange], Dict[str, float]]:
        """Tính toán các thay đổi phạm vi dựa trên lịch sử issues"""
        # Dictionary lưu trữ dữ liệu scope change theo ngày
        daily_scope_points: Dict[str, float] = {}
        scope_changes: List[SprintScopeChange] = []

        # Lấy lịch sử thay đổi sprint của tất cả issues
        sprint_histories = await self.jira_issue_history_db_service.get_sprint_issue_histories(
            sprint_id=sprint_id,
            from_date=start_date,
            to_date=end_date
        )

        # Filter chỉ lấy các thay đổi liên quan đến sprint và story points
        sprint_changes = [h for h in sprint_histories if h.field_name == "sprint"]
        story_point_changes = [h for h in sprint_histories if h.field_name == "story_points"]

        # Phân tích thay đổi sprint
        for change in sprint_changes:
            # Chỉ xét các thay đổi khi issue được thêm vào sprint
            new_value = change.new_value_parsed
            if new_value and str(sprint_id) in str(new_value):
                # Tìm issue tương ứng
                issue = next((i for i in issues if i.jira_issue_id == change.jira_issue_id), None)
                if not issue:
                    continue

                # Ngày thay đổi
                change_date_str = change.created_at.strftime("%Y-%m-%d")

                # Nếu issue được thêm vào sau khi sprint bắt đầu, đây là scope change
                if change.created_at > start_date:
                    points = issue.estimate_point or 0

                    # Cập nhật daily scope points
                    if change_date_str not in daily_scope_points:
                        daily_scope_points[change_date_str] = 0
                    daily_scope_points[change_date_str] += points

                    # Tạo scope change entry
                    existing_change = next(
                        (sc for sc in scope_changes if sc.date.strftime("%Y-%m-%d") == change_date_str),
                        None
                    )

                    if existing_change:
                        existing_change.points_added += points
                        existing_change.issue_keys.append(issue.key)
                    else:
                        scope_changes.append(
                            SprintScopeChange(
                                date=change.created_at,
                                points_added=points,
                                issue_keys=[issue.key]
                            )
                        )

        # Phân tích thay đổi story points
        for change in story_point_changes:
            # Kiểm tra xem issue có thuộc sprint không
            issue = next((i for i in issues if i.jira_issue_id == change.jira_issue_id), None)
            if not issue:
                continue

            # Ngày thay đổi
            change_date_str = change.created_at.strftime("%Y-%m-%d")

            # Tính toán điểm thay đổi
            old_points = float(change.old_value or 0)
            new_points = float(change.new_value or 0)
            points_diff = new_points - old_points

            # Nếu có thay đổi điểm và thời điểm thay đổi sau khi sprint bắt đầu
            if points_diff != 0 and change.created_at > start_date:
                # Cập nhật daily scope points
                if change_date_str not in daily_scope_points:
                    daily_scope_points[change_date_str] = 0
                daily_scope_points[change_date_str] += points_diff

                # Tạo hoặc cập nhật scope change entry
                existing_change = next(
                    (sc for sc in scope_changes if sc.date.strftime("%Y-%m-%d") == change_date_str),
                    None
                )

                if existing_change:
                    existing_change.points_added += points_diff
                    if issue.key not in existing_change.issue_keys:
                        existing_change.issue_keys.append(issue.key)
                else:
                    scope_changes.append(
                        SprintScopeChange(
                            date=change.created_at,
                            points_added=points_diff,
                            issue_keys=[issue.key]
                        )
                    )

        # Sắp xếp scope changes theo ngày
        scope_changes.sort(key=lambda x: x.date)

        return scope_changes, daily_scope_points
