from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus, JiraSprintState
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
            log.error(f"Sprint {sprint_id} not found")
            raise ValueError(f"Sprint {sprint_id} not found")

        # Check if sprint status is active
        if sprint.state != JiraSprintState.ACTIVE.value:
            log.error(f"Sprint {sprint_id} is not active")
            raise ValueError(f"Sprint {sprint.name} is not active")

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
        assert sprint.start_date is not None, "Sprint start date must be provided"
        assert sprint.end_date is not None, "Sprint end date must be provided"

        # Đảm bảo start_date và end_date có timezone
        start_date = sprint.start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
            log.info(f"Added timezone to start_date: {start_date}")

        end_date = sprint.end_date.replace(hour=23, minute=59, second=59,
                                           microsecond=0) if sprint.end_date else datetime.now() + timedelta(days=14)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
            log.info(f"Added timezone to end_date: {end_date}")

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
            try:
                # Tính ideal burndown theo tỷ lệ thời gian
                progress_ratio = i / max(len(days) - 1, 1)  # Tránh chia cho 0
                ideal_remaining = total_points_initial * (1 - progress_ratio)

                # Format ngày hiện tại để so sánh với daily_scope_points
                day_str = day.strftime("%Y-%m-%d")

                # Lấy số điểm được thêm vào cho ngày này
                added_points = daily_scope_points.get(day_str, 0)

                # Tính toán điểm hoàn thành dựa trên trạng thái và hạn của issues
                # Filter issues có trong sprint tính đến ngày day
                sprint_issues = []
                for issue in issues:
                    try:
                        is_in_sprint = await self._is_issue_in_sprint_at_date(issue, sprint.jira_sprint_id, day)
                        if is_in_sprint:
                            sprint_issues.append(issue)
                    except Exception as e:
                        log.error(f"Error checking if issue {issue.key} is in sprint: {str(e)}")
                        log.error(
                            f"Issue created_at: {issue.created_at}, tzinfo: {issue.created_at.tzinfo if issue.created_at else None}")

                # Tính completed_points - những issues đã Done tính đến ngày day
                completed_points = 0
                for issue in sprint_issues:
                    try:
                        is_completed = await self._is_issue_completed_at_date(issue, day)
                        if is_completed:
                            points = await self._get_issue_points_at_date(issue, day)
                            completed_points += points
                    except Exception as e:
                        log.error(f"Error checking if issue {issue.key} is completed: {str(e)}")
                        log.error(
                            f"Issue status: {issue.status}, updated_at: {issue.updated_at}, tzinfo: {issue.updated_at.tzinfo if issue.updated_at else None}")

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
            except Exception as e:
                log.error(f"Error processing day {day}: {str(e)}")
                log.error(f"Day timezone: {day.tzinfo}")
                raise Exception(f"Error processing day {day}: {str(e)}") from e

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

    async def _is_issue_in_sprint_at_date(self, issue: JiraIssueModel, sprint_id: int, date: datetime) -> bool:
        """Kiểm tra xem issue có thuộc sprint vào một ngày cụ thể không"""
        try:
            # Đảm bảo date có timezone
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
                log.info(f"Added timezone to date in _is_issue_in_sprint_at_date: {date}")

            # Nếu issue không có sprint, return False
            if not issue.sprints:
                return False

            # Kiểm tra nếu issue thuộc sprint và được tạo trước hoặc trong ngày đang xét
            for sprint in issue.sprints:
                if sprint and sprint.jira_sprint_id == sprint_id:
                    # Đảm bảo created_at có timezone
                    created_at = issue.created_at
                    if created_at and created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                        log.info(f"Added timezone to issue.created_at: {created_at}")

                    if created_at and created_at <= date:
                        return True

            # Kiểm tra lịch sử thay đổi sprint
            sprint_histories = await self.jira_issue_history_db_service.get_issue_field_history(
                issue.jira_issue_id, "sprint"
            )

            # Tìm thời điểm issue được thêm vào sprint
            for history in sprint_histories:
                # Đảm bảo created_at có timezone
                created_at = history.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)

                new_value = history.new_value_parsed
                if new_value and str(sprint_id) in str(new_value) and created_at <= date:
                    return True

            return False
        except Exception as e:
            log.error(f"Error in _is_issue_in_sprint_at_date: {str(e)}")
            log.error(f"Issue: {issue.key}, sprint_id: {sprint_id}, date: {date}")
            log.error(f"Date timezone: {date.tzinfo}")
            raise

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

    async def _is_issue_completed_at_date(self, issue: JiraIssueModel, date: datetime) -> bool:
        """Kiểm tra xem issue đã hoàn thành tại một ngày cụ thể chưa"""
        try:
            # Đảm bảo date có timezone
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
                log.info(f"Added timezone to date in _is_issue_completed_at_date: {date}")

            # Nếu issue đã có trạng thái Done, kiểm tra thời gian cập nhật
            if issue.status == JiraIssueStatus.DONE and issue.updated_at:
                # Đảm bảo updated_at có timezone
                updated_at = issue.updated_at
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                    log.info(f"Added timezone to issue.updated_at: {updated_at}")
                if updated_at <= date:
                    return True

            # Nếu không, kiểm tra lịch sử thay đổi trạng thái
            status_histories = await self.jira_issue_history_db_service.get_issue_field_history(
                issue.jira_issue_id, "status"
            )

            # Tìm thời điểm issue được chuyển sang trạng thái hoàn thành
            for history in status_histories:
                # Đảm bảo created_at có timezone
                created_at = history.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)

                if (created_at <= date and
                        history.new_value in [JiraIssueStatus.DONE, "Closed", "Resolved"]):
                    return True

            return False
        except Exception as e:
            log.error(f"Error in _is_issue_completed_at_date: {str(e)}")
            log.error(f"Issue: {issue.key}, date: {date}")
            log.error(f"Date timezone: {date.tzinfo}")
            raise

    async def _get_issue_points_at_date(self, issue: JiraIssueModel, date: datetime) -> float:
        """Lấy số điểm của issue tại một ngày cụ thể"""
        try:
            # Đảm bảo date có timezone
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
                log.info(f"Added timezone to date in _get_issue_points_at_date: {date}")

            # Lấy lịch sử thay đổi story points
            points_histories = await self.jira_issue_history_db_service.get_issue_field_history(
                issue.jira_issue_id, "story_points"
            )

            # Nếu không có lịch sử, sử dụng giá trị hiện tại
            if not points_histories:
                return issue.estimate_point or 0

            # Tìm giá trị story points tại ngày cụ thể
            points_at_date = issue.estimate_point or 0
            for history in points_histories:
                # Đảm bảo created_at có timezone
                created_at = history.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)

                if created_at <= date:
                    points_at_date = float(history.new_value or 0)

            return points_at_date
        except Exception as e:
            log.error(f"Error in _get_issue_points_at_date: {str(e)}")
            log.error(f"Issue: {issue.key}, date: {date}")
            log.error(f"Date timezone: {date.tzinfo}")
            raise
