from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_issue_history import JiraIssueHistoryModel
from src.domain.models.jira_performance_summary import UserPerformanceSummaryModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService
from src.domain.services.jira_performance_summary_service import IJiraPerformanceSummaryService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService
from src.domain.services.jira_user_database_service import IJiraUserDatabaseService


class JiraPerformanceSummaryService(IJiraPerformanceSummaryService):
    """Service xử lý thông tin hiệu suất của người dùng"""

    def __init__(
        self,
        jira_issue_db_service: IJiraIssueDatabaseService,
        jira_sprint_db_service: IJiraSprintDatabaseService,
        jira_issue_history_db_service: IJiraIssueHistoryDatabaseService,
        jira_user_db_service: IJiraUserDatabaseService
    ):
        self.jira_issue_db_service = jira_issue_db_service
        self.jira_sprint_db_service = jira_sprint_db_service
        self.jira_issue_history_db_service = jira_issue_history_db_service
        self.jira_user_db_service = jira_user_db_service

    async def get_user_performance_summary(
        self,
        session: AsyncSession,
        user_id: int,
        quarter: int,
        year: int
    ) -> UserPerformanceSummaryModel:
        """Lấy thông tin hiệu suất của người dùng trong một quý"""
        try:
            # Lấy thông tin người dùng
            user = await self.jira_user_db_service.get_user_by_id(session, user_id)
            if not user:
                log.error(f"User {user_id} not found")
                raise ValueError(f"User {user_id} not found")

            # Xác định khoảng thời gian của quý
            start_date, end_date = self._get_quarter_date_range(quarter, year)

            # Lấy danh sách sprints trong quý
            sprints = await self._get_sprints_in_date_range(session, start_date, end_date)

            # Lấy danh sách issues của người dùng trong quý
            issues = await self._get_user_issues_in_date_range(session, user_id, start_date, end_date)

            # Tính toán các chỉ số hiệu suất
            performance_data = await self._calculate_performance_metrics(
                session, user, issues, sprints, start_date, end_date
            )
            # Tạo model kết quả
            return UserPerformanceSummaryModel(
                user_id=user_id,
                user_name=user.name,
                quarter=quarter,
                year=year,
                **performance_data
            )
        except Exception as e:
            log.error(f"Error getting user performance summary: {str(e)}")
            raise

    def _get_quarter_date_range(self, quarter: int, year: int) -> Tuple[datetime, datetime]:
        """Lấy khoảng thời gian của quý"""
        # Xác định tháng bắt đầu và kết thúc của quý
        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3

        # Tạo ngày bắt đầu (ngày 1 của tháng đầu tiên)
        start_date = datetime(year, start_month, 1)

        # Tạo ngày kết thúc (ngày cuối cùng của tháng cuối cùng)
        if end_month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, end_month + 1, 1) - timedelta(days=1)

        return start_date, end_date

    async def _get_sprints_in_date_range(
        self,
        session: AsyncSession,
        start_date: datetime,
        end_date: datetime
    ) -> List[JiraSprintModel]:
        """Lấy danh sách sprints trong khoảng thời gian"""
        # Đảm bảo các datetime objects đều có timezone
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Lấy tất cả sprints của project ZODC
        all_sprints = await self.jira_sprint_db_service.get_all_sprints(session)

        # Lọc sprints trong khoảng thời gian
        sprints_in_range = []
        for sprint in all_sprints:
            if sprint.start_date and sprint.end_date:
                # Đảm bảo sprint dates có timezone
                sprint_start = sprint.start_date.replace(tzinfo=timezone.utc) if sprint.start_date else None
                sprint_end = sprint.end_date.replace(tzinfo=timezone.utc) if sprint.end_date else None

                if sprint_start and sprint_end:
                    # Sprint bắt đầu trong khoảng thời gian hoặc kết thúc trong khoảng thời gian
                    if (start_date <= sprint_start <= end_date) or (start_date <= sprint_end <= end_date):
                        sprints_in_range.append(sprint)

        return sprints_in_range

    async def _get_user_issues_in_date_range(
        self,
        session: AsyncSession,
        user_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[JiraIssueModel]:
        """Lấy danh sách issues của người dùng trong khoảng thời gian"""
        # Đảm bảo các datetime objects đều có timezone
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        # Lấy tất cả issues
        all_issues = await self.jira_issue_db_service.get_issues_by_user_id(session, user_id)

        # Lọc issues của người dùng trong khoảng thời gian
        user_issues = []
        for issue in all_issues:
            # Đảm bảo issue dates có timezone
            issue_created_at = issue.created_at.replace(tzinfo=timezone.utc) if issue.created_at else None
            issue_updated_at = issue.updated_at.replace(tzinfo=timezone.utc) if issue.updated_at else None

            if issue_created_at and issue_updated_at:
                # Issue được tạo trong khoảng thời gian hoặc được cập nhật trong khoảng thời gian
                if (start_date <= issue_created_at <= end_date) or (start_date <= issue_updated_at <= end_date):
                    user_issues.append(issue)

        return user_issues

    async def _calculate_performance_metrics(
        self,
        session: AsyncSession,
        user: JiraUserModel,
        issues: List[JiraIssueModel],
        sprints: List[JiraSprintModel],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Tính toán các chỉ số hiệu suất"""
        # Khởi tạo các biến đếm
        total_tasks: int = len(issues)
        completed_tasks: int = 0
        total_story_points: float = 0
        completed_story_points: float = 0
        total_completion_time: float = 0
        on_time_completions: int = 0
        bug_fixes: int = 0
        successful_bug_fixes: int = 0
        reworks: int = 0

        # Khởi tạo các dictionary đếm theo loại và độ ưu tiên
        task_by_type: Dict[str, int] = {}
        task_by_priority: Dict[str, int] = {}

        # Khởi tạo danh sách hiệu suất theo sprint và tháng
        sprint_performance: List[Dict[str, Any]] = []
        monthly_performance: Dict[str, Dict[str, Any]] = {}

        # Lấy lịch sử thay đổi trạng thái của tất cả issues
        issue_ids = [issue.jira_issue_id for issue in issues]
        status_history_by_issue = await self.jira_issue_history_db_service.get_issues_field_history(
            session, issue_ids, "status"
        )

        # Lấy lịch sử thay đổi story points của tất cả issues
        _ = await self.jira_issue_history_db_service.get_issues_field_history(
            session, issue_ids, "story_points"
        )

        # Duyệt qua từng issue để tính toán các chỉ số
        for issue in issues:
            # Cập nhật số lượng task theo loại
            issue_type = issue.type.value
            if issue_type in task_by_type:
                task_by_type[issue_type] += 1
            else:
                task_by_type[issue_type] = 1

            # Cập nhật số lượng task theo độ ưu tiên
            priority = issue.priority.lower() if issue.priority else "medium"
            if priority in task_by_priority:
                task_by_priority[priority] += 1
            else:
                task_by_priority[priority] = 1

            # Cập nhật story points
            total_story_points += issue.estimate_point or 0

            # Kiểm tra trạng thái hoàn thành
            is_completed = issue.status == JiraIssueStatus.DONE
            if is_completed:
                completed_tasks += 1
                completed_story_points += issue.estimate_point or 0

                # Tính thời gian hoàn thành
                completion_time = self._calculate_completion_time(
                    issue, status_history_by_issue.get(issue.jira_issue_id, [])
                )
                total_completion_time += completion_time

                # Kiểm tra hoàn thành đúng hạn
                if self._is_completed_on_time(issue, completion_time):
                    on_time_completions += 1

                # Kiểm tra bug fix
                if issue_type == JiraIssueType.BUG.value:
                    bug_fixes += 1
                    if not self._has_rework(issue, status_history_by_issue.get(issue.jira_issue_id, [])):
                        successful_bug_fixes += 1

                # Kiểm tra rework
                if self._has_rework(issue, status_history_by_issue.get(issue.jira_issue_id, [])):
                    reworks += 1

            # Cập nhật hiệu suất theo sprint
            for sprint in sprints:
                if self._is_issue_in_sprint(issue, sprint):
                    self._update_sprint_performance(
                        sprint_performance, sprint, issue, is_completed
                    )

            # Cập nhật hiệu suất theo tháng
            month_key = f"{issue.created_at.year}-{issue.created_at.month}"
            if month_key not in monthly_performance:
                monthly_performance[month_key] = {
                    "month": issue.created_at.month,
                    "year": issue.created_at.year,
                    "completed_tasks": 0,
                    "total_tasks": 0,
                    "completed_points": 0,
                    "total_points": 0
                }

            monthly_performance[month_key]["total_tasks"] += 1
            monthly_performance[month_key]["total_points"] += issue.estimate_point or 0

            if is_completed:
                monthly_performance[month_key]["completed_tasks"] += 1
                monthly_performance[month_key]["completed_points"] += issue.estimate_point or 0

        # Tính toán các tỷ lệ
        task_completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        story_point_completion_rate = (completed_story_points / total_story_points *
                                       100) if total_story_points > 0 else 0
        average_completion_time = total_completion_time / completed_tasks if completed_tasks > 0 else 0
        on_time_completion_rate = (on_time_completions / completed_tasks * 100) if completed_tasks > 0 else 0
        bug_fix_rate = (successful_bug_fixes / bug_fixes * 100) if bug_fixes > 0 else 0
        rework_rate = (reworks / completed_tasks * 100) if completed_tasks > 0 else 0

        # Tính toán tỷ lệ hoàn thành cho từng sprint
        for sprint_data in sprint_performance:
            sprint_data["completion_rate"] = (
                sprint_data["completed_tasks"] / sprint_data["total_tasks"] * 100
            ) if sprint_data["total_tasks"] > 0 else 0

        # Tính toán tỷ lệ hoàn thành cho từng tháng
        monthly_performance_list = []
        for month_data in monthly_performance.values():
            month_data["completion_rate"] = (
                month_data["completed_tasks"] / month_data["total_tasks"] * 100
            ) if month_data["total_tasks"] > 0 else 0
            monthly_performance_list.append(month_data)

        # Sắp xếp tháng theo thứ tự
        monthly_performance_list.sort(key=lambda x: (x["year"], x["month"]))

        # Trả về kết quả
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "task_completion_rate": round(task_completion_rate, 2),
            "total_story_points": round(total_story_points, 2),
            "completed_story_points": round(completed_story_points, 2),
            "story_point_completion_rate": round(story_point_completion_rate, 2),
            "average_completion_time": round(average_completion_time, 2),
            "on_time_completion_rate": round(on_time_completion_rate, 2),
            "bug_fix_rate": round(bug_fix_rate, 2),
            "rework_rate": round(rework_rate, 2),
            "task_by_type": task_by_type,
            "task_by_priority": task_by_priority,
            "sprint_performance": sprint_performance,
            "monthly_performance": monthly_performance_list
        }

    def _calculate_completion_time(
        self,
        issue: JiraIssueModel,
        status_histories: List[JiraIssueHistoryModel]
    ) -> float:
        """Tính thời gian hoàn thành của issue (giờ)"""
        # Nếu không có lịch sử, sử dụng thời gian từ created_at đến updated_at
        if not status_histories:
            time_diff = issue.updated_at - issue.created_at
            return time_diff.total_seconds() / 3600  # Chuyển đổi giây thành giờ

        # Tìm thời điểm issue được chuyển sang trạng thái Done
        done_statuses = [JiraIssueStatus.DONE.value, "Done", "DONE"]
        for history in status_histories:
            if history.new_string in done_statuses:
                time_diff = history.created_at - issue.created_at
                return time_diff.total_seconds() / 3600  # Chuyển đổi giây thành giờ

        # Nếu không tìm thấy, sử dụng thời gian từ created_at đến updated_at
        time_diff = issue.updated_at - issue.created_at
        return time_diff.total_seconds() / 3600  # Chuyển đổi giây thành giờ

    def _is_completed_on_time(self, issue: JiraIssueModel, completion_time: float) -> bool:
        """Kiểm tra xem issue có được hoàn thành đúng hạn không"""
        # Nếu issue không có sprint, không thể xác định hạn
        if not issue.sprints:
            return True

        # Lấy sprint đầu tiên
        sprint = issue.sprints[0]

        # Nếu sprint không có ngày kết thúc, không thể xác định hạn
        if not sprint.end_date:
            return True

        # Tính thời gian từ khi tạo đến hạn sprint
        deadline_time = (sprint.end_date - issue.created_at).total_seconds() / 3600  # Chuyển đổi giây thành giờ

        # So sánh thời gian hoàn thành với hạn
        return completion_time <= deadline_time

    def _has_rework(
        self,
        issue: JiraIssueModel,
        status_histories: List[JiraIssueHistoryModel]
    ) -> bool:
        """Kiểm tra xem issue có phải làm lại không"""
        # Sắp xếp lịch sử theo thời gian
        status_histories.sort(key=lambda x: x.created_at)

        # Các trạng thái được coi là hoàn thành
        completed_statuses = [JiraIssueStatus.DONE.value, "Done", "DONE"]

        # Các trạng thái được coi là phải làm lại
        rework_statuses = ["To Do", "TODO", "Open", "Reopened"]

        # Kiểm tra xem issue có chuyển từ trạng thái hoàn thành sang trạng thái phải làm lại không
        was_completed = False
        for history in status_histories:
            if history.new_string in completed_statuses:
                was_completed = True
            elif was_completed and history.new_string in rework_statuses:
                return True

        return False

    def _is_issue_in_sprint(self, issue: JiraIssueModel, sprint: JiraSprintModel) -> bool:
        """Kiểm tra xem issue có thuộc sprint không"""
        for issue_sprint in issue.sprints:
            if issue_sprint.jira_sprint_id == sprint.jira_sprint_id:
                return True
        return False

    def _update_sprint_performance(
        self,
        sprint_performance: List[Dict[str, Any]],
        sprint: JiraSprintModel,
        issue: JiraIssueModel,
        is_completed: bool
    ) -> None:
        """Cập nhật hiệu suất theo sprint"""
        # Tìm sprint trong danh sách
        sprint_data = None
        for data in sprint_performance:
            if data["sprint_id"] == sprint.jira_sprint_id:
                sprint_data = data
                break

        # Nếu chưa có, tạo mới
        if not sprint_data:
            sprint_data = {
                "sprint_id": sprint.jira_sprint_id,
                "sprint_name": sprint.name,
                "start_date": sprint.start_date.strftime("%Y-%m-%d") if sprint.start_date else "",
                "end_date": sprint.end_date.strftime("%Y-%m-%d") if sprint.end_date else "",
                "completed_tasks": 0,
                "total_tasks": 0,
                "completed_points": 0,
                "total_points": 0
            }
            sprint_performance.append(sprint_data)

        # Cập nhật số liệu
        sprint_data["total_tasks"] += 1
        sprint_data["total_points"] += issue.estimate_point or 0

        if is_completed:
            sprint_data["completed_tasks"] += 1
            sprint_data["completed_points"] += issue.estimate_point or 0
