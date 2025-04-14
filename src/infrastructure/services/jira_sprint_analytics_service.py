
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
        added_points = 0
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
        priority_bugs = {
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
        initial_issues: List[JiraIssueModel] = []
        for issue in issues:
            if await self._is_issue_in_sprint_at_date(
                issue,
                sprint.jira_sprint_id,
                start_date,
                sprint_history_by_issue.get(issue.jira_issue_id, [])
            ):
                initial_issues.append(issue)

        log.info(f"Found {len(initial_issues)} initial issues")

        # Tính tổng điểm ban đầu dựa trên lịch sử story points trước sprint start date
        total_points_initial = 0
        for issue in initial_issues:
            try:
                log.info(f"Processing issue {issue.key}:")
                # Lấy lịch sử thay đổi story points từ dữ liệu đã truy vấn
                points_histories = points_history_by_issue.get(issue.jira_issue_id, [])

                log.info(f"Found {len(points_histories)} story points history entries")

                # Lọc các thay đổi trước sprint start date
                pre_sprint_changes = [
                    h for h in points_histories
                    if h.created_at <= start_date
                ]
                log.info(f"created_at: {start_date} and {[h.created_at for h in points_histories]}")

                log.info(f"Found {len(pre_sprint_changes)} changes before sprint start")

                # Sắp xếp theo thời gian, lấy thay đổi gần nhất
                pre_sprint_changes.sort(key=lambda x: x.created_at, reverse=True)

                if pre_sprint_changes:
                    # Lấy giá trị story points gần nhất trước sprint start
                    last_points = pre_sprint_changes[0].new_value
                    try:
                        points = float(last_points) if last_points else 0
                        total_points_initial += points
                        log.info(
                            f"Using points from history: {points} (from change at {pre_sprint_changes[0].created_at})")
                    except (ValueError, TypeError):
                        log.error(f"Error converting story points value: {last_points}")
            except Exception as e:
                log.error(f"Error calculating initial points for issue {issue.key}: {str(e)}")
                continue

        log.info("\n=== FINAL RESULT ===")
        log.info(f"Total initial points: {total_points_initial}")
        log.info("=== END CALCULATING INITIAL POINTS ===\n")

        # Tính toán scope changes và tổng điểm hiện tại
        assert sprint.id is not None, "Sprint ID must be provided"
        scope_changes, daily_scope_points = await self._calculate_scope_changes(
            issues, start_date, end_date, sprint.jira_sprint_id, sprint_history_by_issue, points_history_by_issue
        )

        # Tổng điểm hiện tại = tổng các estimate points của issues trong sprint
        total_points_current = sum(issue.estimate_point for issue in issues)

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
                sprint_issues = []
                for issue in issues:
                    try:
                        is_in_sprint = await self._is_issue_in_sprint_at_date(
                            issue,
                            sprint.jira_sprint_id,
                            day,
                            sprint_history_by_issue.get(issue.jira_issue_id, [])
                        )
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
                        is_completed = await self._is_issue_completed_at_date(
                            issue,
                            day,
                            status_history_by_issue.get(issue.jira_issue_id, [])
                        )
                        if is_completed:
                            points = await self._get_issue_points_at_date(
                                issue,
                                day,
                                points_history_by_issue.get(issue.jira_issue_id, [])
                            )
                            completed_points += points
                            log.info(f"Issue {issue.key} is completed with {points} points on {day_str}")
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
                raise

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

    async def _is_issue_in_sprint_at_date(
        self,
        issue: JiraIssueModel,
        sprint_id: int,
        date: datetime,
        sprint_histories: List[JiraIssueHistoryModel] = None
    ) -> bool:
        """Kiểm tra xem issue có thuộc sprint vào một ngày cụ thể không"""
        try:
            # Nếu issue không có sprint, return False
            if not issue.sprints:
                return False

            # Kiểm tra nếu issue thuộc sprint và được tạo trước hoặc trong ngày đang xét
            for sprint in issue.sprints:
                if sprint and sprint.jira_sprint_id == sprint_id:
                    # Đảm bảo created_at có timezone
                    created_at = issue.created_at
                    if created_at and created_at <= date:
                        return True

            # Kiểm tra lịch sử thay đổi sprint
            if sprint_histories is None:
                sprint_histories = await self.jira_issue_history_db_service.get_issue_field_history(
                    issue.jira_issue_id, "sprint"
                )

            # Tìm thời điểm issue được thêm vào sprint
            for history in sprint_histories:
                # Đảm bảo created_at có timezone
                created_at = history.created_at

                new_value = history.new_value_parsed
                if new_value and str(sprint_id) in str(new_value) and created_at <= date:
                    log.info(f"Issue {issue.key} was added to sprint {sprint_id} at {created_at}")
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
                    new_value = change.new_value_parsed
                    if new_value and str(sprint_id) in str(new_value):
                        # Tìm issue tương ứng
                        issue = next((i for i in issues if i.jira_issue_id == change.jira_issue_id), None)
                        if not issue:
                            continue

                        # Ngày thay đổi
                        change_date_str = change.created_at.strftime("%Y-%m-%d")

                        # Nếu issue được tạo sau sprint start date, đây là scope change
                        if issue.created_at > start_date:
                            # Lấy số điểm của issue tại thời điểm được thêm vào sprint
                            points = await self._get_issue_points_at_date(
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
            log.error(f"Start date: {start_date}, tzinfo: {start_date.tzinfo}")
            log.error(f"End date: {end_date}, tzinfo: {end_date.tzinfo}")
            raise

    async def _is_issue_completed_at_date(
        self,
        issue: JiraIssueModel,
        date: datetime,
        status_histories: List[JiraIssueHistoryModel] = None
    ) -> bool:
        """Kiểm tra xem issue đã hoàn thành tại một ngày cụ thể chưa"""
        try:
            # Đảm bảo date có timezone
            # if date.tzinfo is None:
            #     date = date.replace(tzinfo=timezone.utc)

            # Nếu issue đã có trạng thái Done, kiểm tra thời gian cập nhật
            if issue.status == JiraIssueStatus.DONE and issue.updated_at:
                # Đảm bảo updated_at có timezone
                updated_at = issue.updated_at
                # if updated_at.tzinfo is None:
                #     updated_at = updated_at.replace(tzinfo=timezone.utc)
                if updated_at <= date:
                    return True

            # Nếu không, kiểm tra lịch sử thay đổi trạng thái
            # if status_histories is None:
            #     status_histories = await self.jira_issue_history_db_service.get_issue_field_history(
            #         issue.jira_issue_id, "status"
            #     )

            # Danh sách các trạng thái được coi là hoàn thành
            completed_statuses = [
                JiraIssueStatus.DONE,
                "Done",
                "DONE",
                "Closed",
                "CLOSED",
                "Resolved",
                "RESOLVED"
            ]

            # Tìm thời điểm issue được chuyển sang trạng thái hoàn thành
            for history in status_histories:
                # Đảm bảo created_at có timezone
                created_at = history.created_at
                # if created_at.tzinfo is None:
                #     created_at = created_at.replace(tzinfo=timezone.utc)

                if (created_at <= date and history.new_value in completed_statuses):
                    return True

            return False
        except Exception as e:
            log.error(f"Error in _is_issue_completed_at_date: {str(e)}")
            log.error(f"Issue: {issue.key}, date: {date}")
            log.error(f"Date timezone: {date.tzinfo}")
            raise

    async def _get_issue_points_at_date(
        self,
        issue: JiraIssueModel,
        date: datetime,
        points_histories: List[JiraIssueHistoryModel] = None
    ) -> float:
        """Lấy số điểm của issue tại một ngày cụ thể"""
        try:
            # Đảm bảo date có timezone
            # if date.tzinfo is None:
            #     date = date.replace(tzinfo=timezone.utc)

            # Lấy lịch sử thay đổi story points nếu chưa có
            # if points_histories is None:
            #     points_histories = await self.jira_issue_history_db_service.get_issue_field_history(
            #         issue.jira_issue_id, "story_points"
            #     )

            # Nếu không có lịch sử, sử dụng giá trị hiện tại
            if not points_histories:
                return issue.estimate_point or 0

            # Tìm giá trị story points tại ngày cụ thể
            points_at_date = issue.estimate_point or 0
            for history in points_histories:
                # Đảm bảo created_at có timezone
                created_at = history.created_at
                # if created_at.tzinfo is None:
                #     created_at = created_at.replace(tzinfo=timezone.utc)

                if created_at <= date:
                    try:
                        points_at_date = float(history.new_value or 0)
                    except (ValueError, TypeError):
                        log.error(f"Error converting story points value: {history.new_value}")
                        # Giữ nguyên giá trị cũ nếu không thể chuyển đổi

            return points_at_date
        except Exception as e:
            log.error(f"Error in _get_issue_points_at_date: {str(e)}")
            log.error(f"Issue: {issue.key}, date: {date}")
            log.error(f"Date timezone: {date.tzinfo}")
            raise
