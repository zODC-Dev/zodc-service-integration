from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType, JiraSprintState
from src.domain.models.apis.jira_user import JiraAssigneeResponse
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_issue_history import JiraIssueHistoryModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_sprint_analytics import (
    BugChartModel,
    BugPriorityCountModel,
    BugReportDataModel,
    BugTaskModel,
    DailySprintData,
    SprintAnalyticsBaseModel,
    SprintBurndownModel,
    SprintBurnupModel,
    SprintGoalModel,
    SprintScopeChange,
    TaskReportModel,
    WorkloadModel,
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

        # # Check if sprint status is active
        # if sprint.state != JiraSprintState.ACTIVE.value:
        #     log.error(f"Sprint {sprint_id} is not active")
        #     raise ValueError(f"Sprint {sprint.name} is not active")

        # Lấy danh sách issues trong sprint
        issues = await self._get_sprint_issues(user_id, project_key, sprint_id)
        log.debug(f"Issues count: {len(issues)}")

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

    async def get_sprint_goal_data(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintGoalModel:
        """Lấy dữ liệu sprint goal cho một sprint"""
        # Lấy thông tin sprint
        sprint = await self._get_sprint_details(sprint_id)
        if not sprint:
            log.error(f"Không tìm thấy sprint {sprint_id}")
            raise ValueError(f"Sprint {sprint_id} not found")

        # Lấy danh sách issues trong sprint
        issues = await self._get_sprint_issues(user_id, project_key, sprint_id)

        # Phân loại issues theo trạng thái
        completed_issues = []
        in_progress_issues = []
        to_do_issues = []

        for issue in issues:
            if issue.status == JiraIssueStatus.DONE:
                completed_issues.append(issue)
            elif issue.status in [JiraIssueStatus.IN_PROGRESS, JiraIssueStatus.IN_REVIEW]:
                in_progress_issues.append(issue)
            else:
                to_do_issues.append(issue)

        # Tính toán số lượng tasks và điểm cho mỗi loại
        total_issues = len(issues)
        total_points = sum(issue.estimate_point or 0 for issue in issues)

        # Tính toán cho completed tasks
        completed_points = sum(issue.estimate_point or 0 for issue in completed_issues)
        completed_percentage = (len(completed_issues) / total_issues * 100) if total_issues > 0 else 0

        # Tính toán cho in progress tasks
        in_progress_points = sum(issue.estimate_point or 0 for issue in in_progress_issues)
        in_progress_percentage = (len(in_progress_issues) / total_issues * 100) if total_issues > 0 else 0

        # Tính toán cho to do tasks
        to_do_points = sum(issue.estimate_point or 0 for issue in to_do_issues)
        to_do_percentage = (len(to_do_issues) / total_issues * 100) if total_issues > 0 else 0

        # Tính toán added points (tổng điểm của các issues được thêm vào sau khi sprint bắt đầu)
        added_points: float = 0
        if sprint.start_date:
            for issue in issues:
                if issue.created_at and issue.created_at > sprint.start_date:
                    added_points += issue.estimate_point or 0

        # Tạo các TaskReportModel
        completed_tasks = TaskReportModel(
            number_of_tasks=len(completed_issues),
            percentage=round(completed_percentage, 2),
            points=round(completed_points, 2)
        )

        in_progress_tasks = TaskReportModel(
            number_of_tasks=len(in_progress_issues),
            percentage=round(in_progress_percentage, 2),
            points=round(in_progress_points, 2)
        )

        to_do_tasks = TaskReportModel(
            number_of_tasks=len(to_do_issues),
            percentage=round(to_do_percentage, 2),
            points=round(to_do_points, 2)
        )

        # Tạo và trả về SprintGoalModel
        return SprintGoalModel(
            id=str(sprint_id),
            goal=sprint.goal or "",
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            to_do_tasks=to_do_tasks,
            added_points=round(added_points, 2),
            total_points=round(total_points, 2)
        )

    async def get_bug_report_data(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> BugReportDataModel:
        """Lấy dữ liệu báo cáo bug cho một sprint"""
        # Lấy thông tin sprint
        sprint = await self._get_sprint_details(sprint_id)
        if not sprint:
            log.error(f"Không tìm thấy sprint {sprint_id}")
            raise ValueError(f"Sprint {sprint_id} not found")

        # Lấy danh sách issues trong sprint
        issues = await self._get_sprint_issues(user_id, project_key, sprint_id)

        # Lọc các issues là bug
        bug_issues = [issue for issue in issues if issue.type == JiraIssueType.BUG]

        # Phân loại bugs theo priority
        priority_bugs: Dict[str, List[JiraIssueModel]] = {
            "lowest": [],
            "low": [],
            "medium": [],
            "high": [],
            "highest": []
        }

        for bug in bug_issues:
            priority = bug.priority.name.lower() if bug.priority else "medium"
            if priority in priority_bugs:
                priority_bugs[priority].append(bug)
            else:
                # Default to medium if priority is not recognized
                priority_bugs["medium"].append(bug)

        # Tạo BugPriorityCountModel
        priority_count = BugPriorityCountModel(
            lowest=len(priority_bugs["lowest"]),
            low=len(priority_bugs["low"]),
            medium=len(priority_bugs["medium"]),
            high=len(priority_bugs["high"]),
            highest=len(priority_bugs["highest"])
        )

        # Tạo BugChartModel
        bug_chart = BugChartModel(
            priority=priority_count,
            total=len(bug_issues)
        )

        # Tạo danh sách BugTaskModel
        bug_tasks = []
        for bug in bug_issues:
            bug_task = BugTaskModel(
                id=str(bug.jira_issue_id),
                key=bug.key,
                link=bug.link_url or f"https://jira.example.com/browse/{bug.key}",  # Use link_url if available
                summary=bug.summary,
                points=bug.estimate_point or 0,
                priority=bug.priority.name if bug.priority else "Medium",
                status=bug.status,
                assignee=JiraAssigneeResponse.from_domain(bug.assignee) if bug.assignee else None,
                created_at=bug.created_at,
                updated_at=bug.updated_at
            )
            bug_tasks.append(bug_task)

        # Tạo và trả về BugReportDataModel
        return BugReportDataModel(
            bugs=bug_tasks,
            bugs_chart=[bug_chart]  # For now, we only have one chart
        )

    async def _get_sprint_details(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """Lấy thông tin chi tiết của sprint bằng id"""
        return await self.jira_sprint_db_service.get_sprint_by_id(sprint_id)

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

        # # Đảm bảo start_date và end_date có timezone
        start_date = sprint.start_date
        end_date = sprint.end_date

        log.info("=== START CALCULATING INITIAL POINTS ===")
        log.info(f"Sprint start date: {start_date}")

        # Chuẩn bị danh sách issue IDs cho các truy vấn batch
        all_issue_ids = [issue.jira_issue_id for issue in issues]

        # Lấy tất cả sprint histories trong một lần truy vấn
        sprint_history_by_issue = await self.jira_issue_history_db_service.get_issues_field_history(
            all_issue_ids, "sprint"
        )

        # Lấy tất cả story points histories trong một lần truy vấn
        points_history_by_issue = await self.jira_issue_history_db_service.get_issues_field_history(
            all_issue_ids, "story_points"
        )

        # Lấy tất cả status histories trong một lần truy vấn
        status_history_by_issue = await self.jira_issue_history_db_service.get_issues_field_history(
            all_issue_ids, "status"
        )

        # Tìm các initial issues (issues có trong sprint tại thời điểm sprint bắt đầu)
        log.info(f"len(issues): {len(issues)}")
        initial_issues = self._get_initial_issues(issues, start_date)
        log.info(f"len(initial_issues): {len(initial_issues)}")

        total_points_initial = self._calculate_initial_points(
            initial_issues,
            points_history_by_issue,
            start_date
        )

        log.info("\n=== FINAL RESULT ===")
        log.info(f"Total initial points: {total_points_initial}")
        log.info("=== END CALCULATING INITIAL POINTS ===\n")

        # Tính toán scope changes và tổng điểm hiện tại
        assert sprint.id is not None, "Sprint ID must be provided"
        scope_changes, daily_scope_points = self._calculate_scope_changes(
            issues, start_date, end_date, sprint.jira_sprint_id, sprint_history_by_issue, points_history_by_issue
        )

        # Tổng điểm hiện tại = tổng các estimate points của issues trong sprint
        total_points_current = sum(issue.estimate_point for issue in issues)

        daily_data = self._calculate_daily_data(
            issues, sprint, start_date, end_date, total_points_initial, daily_scope_points, sprint_history_by_issue, status_history_by_issue, points_history_by_issue
        )

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

    def _is_issue_in_sprint_at_date(
        self,
        issue: JiraIssueModel,
        jira_sprint_id: int,
        date: datetime,
        sprint_histories: List[JiraIssueHistoryModel] = None
    ) -> bool:
        """Kiểm tra xem issue có thuộc sprint vào một ngày cụ thể không"""
        # case 1: issue created after date being checked
        if issue.created_at and issue.created_at > date:
            return False

        # Tìm thời điểm issue được thêm vào sprint
        for history in sprint_histories:
            # Handle the case where new_value contains comma-separated sprint IDs
            if history.created_at <= date and self._is_sprint_id_in_value(jira_sprint_id, history.new_value):
                return True

        return False

    def _calculate_scope_changes(
        self,
        issues: List[JiraIssueModel],
        start_date: datetime,
        end_date: datetime,
        sprint_id: int,
        sprint_history_by_issue: Dict[str, List[JiraIssueHistoryModel]] = None,
        story_point_history_by_issue: Dict[str, List[JiraIssueHistoryModel]] = None
    ) -> Tuple[List[SprintScopeChange], Dict[str, float]]:
        """Tính toán các thay đổi phạm vi dựa trên lịch sử issues"""
        try:
            # Dictionary lưu trữ dữ liệu scope change theo ngày
            daily_scope_points: Dict[str, float] = {}
            scope_changes: List[SprintScopeChange] = []

            # Lấy tất cả các thay đổi sprint sau sprint start date
            sprint_changes: List[JiraIssueHistoryModel] = []
            for _, histories in sprint_history_by_issue.items():
                for history in histories:
                    if start_date <= history.created_at <= end_date:
                        sprint_changes.append(history)

            # Lấy tất cả các thay đổi story points sau sprint start date
            story_point_changes: List[JiraIssueHistoryModel] = []
            for _, histories in story_point_history_by_issue.items():
                for history in histories:
                    if start_date <= history.created_at <= end_date:
                        story_point_changes.append(history)

            # Sắp xếp thay đổi theo ngày
            sprint_changes.sort(key=lambda x: x.created_at)
            story_point_changes.sort(key=lambda x: x.created_at)

            # Phân tích thay đổi sprint
            for change in sprint_changes:
                try:
                    # Chỉ xét các thay đổi khi issue được thêm vào sprint
                    new_value = change.new_value
                    # Handle the case where new_value contains comma-separated sprint IDs
                    if self._is_sprint_id_in_value(sprint_id, new_value):
                        # Tìm issue tương ứng
                        issue = next((i for i in issues if i.jira_issue_id == change.jira_issue_id), None)
                        if not issue:
                            continue

                        # Ngày thay đổi
                        change_date_str = change.created_at.strftime("%Y-%m-%d")

                        # Nếu issue được tạo sau sprint start date, đây là scope change
                        if issue.created_at > start_date:
                            # Lấy số điểm của issue tại thời điểm được thêm vào sprint
                            points = self._get_issue_points_at_date(
                                issue,
                                change.created_at,
                                story_point_history_by_issue.get(
                                    issue.jira_issue_id, []) if story_point_history_by_issue else None
                            )

                            log.info(f"Issue {issue.key} added to sprint with {points} points at {change.created_at}")

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
                                if issue.key not in existing_change.issue_keys:
                                    existing_change.issue_keys.append(issue.key)
                            else:
                                scope_changes.append(
                                    SprintScopeChange(
                                        date=change.created_at,
                                        points_added=points,
                                        issue_keys=[issue.key]
                                    )
                                )
                except Exception as e:
                    log.error(f"Error processing sprint change: {str(e)}")
                    continue

            # Phân tích thay đổi story points
            for change in story_point_changes:
                try:
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

                    # Nếu có thay đổi điểm
                    if points_diff != 0:
                        log.info(
                            f"Issue {issue.key} story points changed from {old_points} to {new_points} at {change.created_at}")

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
                except Exception as e:
                    log.error(f"Error processing story point change: {str(e)}")
                    continue

            # Sắp xếp scope changes theo ngày
            scope_changes.sort(key=lambda x: x.date)

            return scope_changes, daily_scope_points
        except Exception as e:
            log.error(f"Error in _calculate_scope_changes: {str(e)}")
            raise

    def _is_issue_completed_at_date(
        self,
        issue: JiraIssueModel,
        date: datetime,
        status_histories: List[JiraIssueHistoryModel] = None
    ) -> bool:
        """Kiểm tra xem issue đã hoàn thành tại một ngày cụ thể chưa"""
        # Nếu issue đã có trạng thái Done, kiểm tra thời gian cập nhật
        if issue.status == JiraIssueStatus.DONE and issue.updated_at:
            if issue.updated_at <= date:
                return True

        # Danh sách các trạng thái được coi là hoàn thành
        completed_statuses = [
            JiraIssueStatus.DONE,
            "Done",
            "DONE"
        ]

        # Tìm thời điểm issue được chuyển sang trạng thái hoàn thành
        for history in status_histories:
            if (history.created_at <= date and history.new_string in completed_statuses):
                return True

        return False

    def _get_issue_points_at_date(
        self,
        issue: JiraIssueModel,
        date: datetime,
        points_histories: List[JiraIssueHistoryModel] = None
    ) -> float:
        """Lấy số điểm của issue tại một ngày cụ thể"""
        # Nếu không có lịch sử, sử dụng giá trị hiện tại
        if not points_histories:
            return issue.estimate_point or 0

        # Tìm giá trị story points tại ngày cụ thể
        points_at_date = issue.estimate_point or 0
        for history in points_histories:
            if history.created_at <= date:
                try:
                    points_at_date = float(history.new_string or 0)
                except (ValueError, TypeError):
                    log.error(f"Error converting story points value: {history.new_string}")

        return points_at_date

    def _get_initial_issues(
        self,
        issues: List[JiraIssueModel],
        start_date: datetime,
    ) -> List[JiraIssueModel]:
        """By pass issues created before sprint start date"""
        initial_issues = [issue for issue in issues if issue.created_at <= start_date]
        return initial_issues

    def _calculate_initial_points(
        self,
        initial_issues: List[JiraIssueModel],
        initial_points_histories: Dict[str, List[JiraIssueHistoryModel]],
        start_date: datetime
    ) -> float:
        """Tính toán số điểm của issues ban đầu"""
        """Need to hanlde 2 cases
        1. Issue have points change history before sprint start date, then use latest point change history before sprint start date
        2. Issue created before sprint start date with points and no points change history before sprint start date, then use points of issue
        """
        total_initial_points: float = 0
        for issue in initial_issues:
            point_change_histories: List[JiraIssueHistoryModel] = initial_points_histories.get(issue.jira_issue_id, [])

            # sort point change histories by created_at, and get the latest point change history before sprint start date
            point_change_histories.sort(key=lambda x: x.created_at)
            latest_point_change_history = next(
                (history for history in point_change_histories if history.created_at <= start_date), None)

            # case 1: issue created before sprint start date with points and no points change history before sprint start date, then use points of issue
            if issue.estimate_point and len(point_change_histories) == 0:
                total_initial_points += issue.estimate_point
            # case 2: issue created before sprint start date and have points change history before sprint start date, then use latest point change history before sprint start date
            elif latest_point_change_history:
                latest_point = float(latest_point_change_history.new_string or 0)
                total_initial_points += latest_point
            else:
                total_initial_points += 0

        log.info(f"Total initial points: {total_initial_points}")
        return total_initial_points

    def _calculate_daily_data(
        self,
        issues: List[JiraIssueModel],
        sprint: JiraSprintModel,
        start_date: datetime,
        end_date: datetime,
        total_points_initial: float,
        daily_scope_points: Dict[str, float],
        sprint_history_by_issue: Dict[str, List[JiraIssueHistoryModel]],
        status_history_by_issue: Dict[str, List[JiraIssueHistoryModel]],
        points_history_by_issue: Dict[str, List[JiraIssueHistoryModel]]
    ) -> List[DailySprintData]:
        """Tính toán dữ liệu hàng ngày cho mỗi ngày trong khoảng thời gian"""
        daily_data: List[DailySprintData] = []

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
                log.info(f"Checking issues for day: {day_str}, day timezone: {day.tzinfo}")
                sprint_issues = [issue for issue in issues if self._is_issue_in_sprint_at_date(
                    issue, sprint.jira_sprint_id, day, sprint_history_by_issue.get(issue.jira_issue_id, []))]

                # Tính completed_points - những issues đã Done tính đến ngày day
                completed_points: float = 0
                for issue in sprint_issues:
                    is_completed = self._is_issue_completed_at_date(
                        issue,
                        day,
                        status_history_by_issue.get(issue.jira_issue_id, [])
                    )

                    if not is_completed:
                        continue

                    points = self._get_issue_points_at_date(
                        issue,
                        day,
                        points_history_by_issue.get(issue.jira_issue_id, [])
                    )
                    completed_points += points
                    log.info(f"Issue {issue.key} is completed with {points} points on {day_str}")

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
                raise

        return daily_data

    def _is_sprint_id_in_value(self, sprint_id: int, value: Optional[str]) -> bool:
        """Kiểm tra xem một sprint ID có nằm trong giá trị không (có thể là chuỗi chứa nhiều ID ngăn cách bởi dấu phẩy)"""
        if not value:
            return False

        if ',' in value:
            # Split by comma and check if our sprint ID is in the list
            sprint_ids = [id.strip() for id in value.split(',')]
            return str(sprint_id) in sprint_ids
        else:
            # Single ID
            return value.isdigit() and int(value) == sprint_id

    async def get_team_workload_data(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> List[WorkloadModel]:
        """Lấy dữ liệu workload của các thành viên trong sprint"""
        # Lấy thông tin sprint
        sprint = await self._get_sprint_details(sprint_id)
        if not sprint:
            log.error(f"Sprint {sprint_id} not found")
            raise ValueError(f"Sprint {sprint_id} not found")

        # Lấy danh sách issues trong sprint
        issues = await self._get_sprint_issues(user_id, project_key, sprint_id)

        # Lưu trữ workload theo thành viên
        workload_by_member: Dict[str, Dict[str, float]] = {}

        # Duyệt qua từng issue để tính toán workload
        for issue in issues:
            # Bỏ qua issue không có assignee
            if not issue.assignee:
                continue

            user_name = issue.assignee.name

            # Khởi tạo dữ liệu workload cho thành viên nếu chưa có
            if user_name not in workload_by_member:
                workload_by_member[user_name] = {
                    "completed_points": 0,
                    "remaining_points": 0
                }

            # Tính toán điểm dựa vào trạng thái issue
            points = issue.estimate_point or 0

            if issue.status == JiraIssueStatus.DONE:
                workload_by_member[user_name]["completed_points"] += points
            else:
                workload_by_member[user_name]["remaining_points"] += points

        # Chuyển đổi dữ liệu sang model
        result: List[WorkloadModel] = []
        for user_name, points in workload_by_member.items():
            result.append(
                WorkloadModel(
                    user_name=user_name,
                    completed_points=round(points["completed_points"], 2),
                    remaining_points=round(points["remaining_points"], 2)
                )
            )

        # Sắp xếp kết quả theo tổng số điểm (giảm dần)
        result.sort(
            key=lambda x: (x.completed_points + x.remaining_points),
            reverse=True
        )

        return result
