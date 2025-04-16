from datetime import datetime
from typing import List

from src.app.schemas.responses.jira_sprint_analytics import (
    BugChartResponse,
    BugPriorityCountResponse,
    BugReportDataResponse,
    BugTaskResponse,
    SprintBurndownResponse,
    SprintBurnupResponse,
    SprintGoalResponse,
    TaskReportResponse,
)
from src.configs.logger import log
from src.domain.models.apis.jira_user import JiraAssigneeResponse
from src.domain.services.jira_sprint_analytics_service import IJiraSprintAnalyticsService


class JiraSprintAnalyticsApplicationService:
    """Application service cho các sprint analytics charts"""

    def __init__(self, sprint_analytics_service: IJiraSprintAnalyticsService):
        self.sprint_analytics_service = sprint_analytics_service

    def _round_float_list(self, float_list: List[float]) -> List[float]:
        """Làm tròn danh sách các số thập phân đến 2 chữ số"""
        return [round(value, 2) for value in float_list]

    async def get_sprint_burndown_chart(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurndownResponse:
        """Lấy dữ liệu cho biểu đồ burndown của một sprint"""
        try:
            burndown_data = await self.sprint_analytics_service.get_sprint_burndown_data(
                user_id, project_key, sprint_id
            )

            # Get current date
            current_date = datetime.now().date()

            # Process actual burndown - set values to None for future dates
            actual_burndown = []
            dates = burndown_data.get_dates_list()
            raw_actual_burndown = burndown_data.get_actual_burndown()

            for i, date_str in enumerate(dates):
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if date <= current_date:
                    # For dates up to today, use actual value
                    actual_burndown.append(round(raw_actual_burndown[i], 2))
                else:
                    # For future dates, use None
                    actual_burndown.append(None)

            # Chuyển đổi domain model sang response DTO với các giá trị đã làm tròn
            return SprintBurndownResponse(
                sprint_name=burndown_data.name,
                start_date=burndown_data.start_date.strftime("%Y-%m-%d"),
                end_date=burndown_data.end_date.strftime("%Y-%m-%d"),
                total_points_initial=round(burndown_data.total_points_initial, 2),
                total_points_current=round(burndown_data.total_points_current, 2),
                dates=dates,
                ideal_burndown=self._round_float_list(burndown_data.get_ideal_burndown()),
                actual_burndown=actual_burndown,
                added_points=self._round_float_list(burndown_data.get_added_points()),
                scope_changes=[
                    {
                        "date": change.date.strftime("%Y-%m-%d"),
                        "pointsAdded": round(change.points_added, 2),
                        "issueKeys": change.issue_keys
                    }
                    for change in burndown_data.scope_changes
                ] if burndown_data.scope_changes else None
            )
        except Exception as e:
            log.error(f"Error getting sprint burndown chart: {str(e)}")
            raise

    async def get_sprint_burnup_chart(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurnupResponse:
        """Lấy dữ liệu cho biểu đồ burnup của một sprint"""
        try:
            burnup_data = await self.sprint_analytics_service.get_sprint_burnup_data(
                user_id, project_key, sprint_id
            )

            # Tính toán ideal burnup line
            ideal_burnup = [
                burnup_data.total_points_initial * (i / max(len(burnup_data.daily_data) - 1, 1))
                for i, _ in enumerate(burnup_data.daily_data)
            ]

            # Get current date
            current_date = datetime.now().date()

            # Process actual burnup - set values to None for future dates
            actual_burnup = []
            dates = burnup_data.get_dates_list()
            raw_actual_burnup = burnup_data.get_actual_burnup()

            # Process scope line - set values to None for future dates
            scope_line = []
            raw_scope_line = burnup_data.get_scope_line()

            for i, date_str in enumerate(dates):
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if date <= current_date:
                    # For dates up to today, use actual value
                    actual_burnup.append(round(raw_actual_burnup[i], 2))
                    scope_line.append(round(raw_scope_line[i], 2))
                else:
                    # For future dates, use None
                    actual_burnup.append(None)
                    scope_line.append(round(raw_scope_line[i], 2))  # Keep scope line values for future dates

            # Chuyển đổi domain model sang response DTO với các giá trị đã làm tròn
            return SprintBurnupResponse(
                sprint_name=burnup_data.name,
                start_date=burnup_data.start_date.strftime("%Y-%m-%d"),
                end_date=burnup_data.end_date.strftime("%Y-%m-%d"),
                total_points_initial=round(burnup_data.total_points_initial, 2),
                total_points_current=round(burnup_data.total_points_current, 2),
                dates=dates,
                ideal_burnup=self._round_float_list(ideal_burnup),
                actual_burnup=actual_burnup,
                scope_line=scope_line,
                added_points=self._round_float_list(burnup_data.get_added_points()),
                scope_changes=[
                    {
                        "date": change.date.strftime("%Y-%m-%d"),
                        "points_added": round(change.points_added, 2),
                        "issueKeys": change.issue_keys
                    }
                    for change in burnup_data.scope_changes
                ] if burnup_data.scope_changes else None
            )
        except Exception as e:
            log.error(f"Error getting sprint burnup chart: {str(e)}")
            raise

    async def get_sprint_goal(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintGoalResponse:
        """Lấy dữ liệu sprint goal cho một sprint"""
        try:
            goal_data = await self.sprint_analytics_service.get_sprint_goal_data(
                user_id, project_key, sprint_id
            )

            # Chuyển đổi domain model sang response DTO
            return SprintGoalResponse(
                id=goal_data.id,
                goal=goal_data.goal,
                completed_tasks=TaskReportResponse(
                    number_of_tasks=goal_data.completed_tasks.number_of_tasks,
                    percentage=goal_data.completed_tasks.percentage,
                    points=goal_data.completed_tasks.points
                ),
                in_progress_tasks=TaskReportResponse(
                    number_of_tasks=goal_data.in_progress_tasks.number_of_tasks,
                    percentage=goal_data.in_progress_tasks.percentage,
                    points=goal_data.in_progress_tasks.points
                ),
                to_do_tasks=TaskReportResponse(
                    number_of_tasks=goal_data.to_do_tasks.number_of_tasks,
                    percentage=goal_data.to_do_tasks.percentage,
                    points=goal_data.to_do_tasks.points
                ),
                added_points=goal_data.added_points,
                total_points=goal_data.total_points
            )
        except Exception as e:
            log.error(f"Error getting sprint goal: {str(e)}")
            raise

    async def get_bug_report(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> BugReportDataResponse:
        """Lấy dữ liệu báo cáo bug cho một sprint"""
        try:
            bug_data = await self.sprint_analytics_service.get_bug_report_data(
                user_id, project_key, sprint_id
            )

            # Chuyển đổi domain model sang response DTO
            bug_tasks = []
            for bug in bug_data.bugs:
                # Create assignee response if assignee exists
                assignee_response = None
                if bug.assignee:
                    assignee_response = JiraAssigneeResponse(
                        id=bug.assignee.id,
                        jira_account_id=bug.assignee.jira_account_id,
                        email=bug.assignee.email,
                        avatar_url=bug.assignee.avatar_url,
                        name=bug.assignee.name,
                        is_system_user=bug.assignee.is_system_user
                    )

                bug_task = BugTaskResponse(
                    id=bug.id,
                    key=bug.key,
                    link=bug.link,
                    summary=bug.summary,
                    points=bug.points,
                    priority=bug.priority,
                    status=bug.status.value,
                    assignee=assignee_response,
                    created_at=bug.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    updated_at=bug.updated_at.strftime("%Y-%m-%d %H:%M:%S")
                )
                bug_tasks.append(bug_task)

            bug_charts = []
            for chart in bug_data.bugs_chart:
                bug_chart = BugChartResponse(
                    priority=BugPriorityCountResponse(
                        lowest=chart.priority.lowest,
                        low=chart.priority.low,
                        medium=chart.priority.medium,
                        high=chart.priority.high,
                        highest=chart.priority.highest
                    ),
                    total=chart.total
                )
                bug_charts.append(bug_chart)

            return BugReportDataResponse(
                bugs=bug_tasks,
                bugs_chart=bug_charts
            )
        except Exception as e:
            log.error(f"Error getting bug report: {str(e)}")
            raise
