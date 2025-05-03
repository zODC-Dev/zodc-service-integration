from datetime import datetime
from typing import Dict, List

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.schemas.responses.gantt_chart import GanttTaskResponse
from src.app.schemas.responses.jira_sprint_analytics import (
    BugChartResponse,
    BugPriorityCountResponse,
    BugReportDataResponse,
    BugTaskResponse,
    SprintBurndownResponse,
    SprintBurnupResponse,
    SprintGoalResponse,
    TaskReportResponse,
    WorkloadResponse,
)
from src.configs.logger import log
from src.domain.models.apis.jira_user import JiraAssigneeResponse
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.services.jira_sprint_analytics_service import IJiraSprintAnalyticsService


class JiraSprintAnalyticsApplicationService:
    """Application service cho các sprint analytics charts"""

    def __init__(self, sprint_analytics_service: IJiraSprintAnalyticsService, jira_sprint_repository: IJiraSprintRepository, jira_issue_repository: IJiraIssueRepository):
        self.sprint_analytics_service = sprint_analytics_service
        self.jira_sprint_repository = jira_sprint_repository
        self.jira_issue_repository = jira_issue_repository

    def _round_float_list(self, float_list: List[float]) -> List[float]:
        """Làm tròn danh sách các số thập phân đến 2 chữ số"""
        return [round(value, 2) for value in float_list]

    async def get_sprint_burndown_chart(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurndownResponse:
        """Lấy dữ liệu cho biểu đồ burndown của một sprint"""
        try:
            burndown_data = await self.sprint_analytics_service.get_sprint_burndown_data(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )

            # Get current date
            current_date = datetime.now().date()

            # Process actual burndown - set values to None for future dates
            actual_burndown: List[float | None] = []
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
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintBurnupResponse:
        """Lấy dữ liệu cho biểu đồ burnup của một sprint"""
        try:
            burnup_data = await self.sprint_analytics_service.get_sprint_burnup_data(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )

            # Tính toán ideal burnup line
            ideal_burnup = [
                burnup_data.total_points_initial * (i / max(len(burnup_data.daily_data) - 1, 1))
                for i, _ in enumerate(burnup_data.daily_data)
            ]

            # Get current date
            current_date = datetime.now().date()

            # Process actual burnup - set values to None for future dates
            actual_burnup: List[float | None] = []
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
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> SprintGoalResponse:
        """Lấy dữ liệu sprint goal cho một sprint"""
        try:
            goal_data = await self.sprint_analytics_service.get_sprint_goal_data(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
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
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> BugReportDataResponse:
        """Lấy dữ liệu báo cáo bug cho một sprint"""
        try:
            bug_data = await self.sprint_analytics_service.get_bug_report_data(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
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

    async def get_team_workload(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> List[WorkloadResponse]:
        """Lấy dữ liệu workload của các thành viên trong sprint"""
        try:
            workload_data = await self.sprint_analytics_service.get_team_workload_data(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )

            # Chuyển đổi domain model sang response DTO
            return [
                WorkloadResponse(
                    user_name=item.user_name,
                    completed_points=item.completed_points,
                    remaining_points=item.remaining_points
                )
                for item in workload_data
            ]
        except Exception as e:
            log.error(f"Error getting team workload: {str(e)}")
            raise

    async def get_gantt_chart_data(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> List[GanttTaskResponse]:
        """Get Gantt chart data for a sprint"""
        try:
            # Get sprint data
            sprint = await self.jira_sprint_repository.get_sprint_by_id(session=session, sprint_id=sprint_id)
            if not sprint:
                raise ValueError(f"Sprint with ID {sprint_id} not found")

            # Get all issues in the sprint
            issues = await self.jira_issue_repository.get_project_issues(session=session, project_key=project_key, sprint_id=sprint_id)

            # Group tasks by their story_id for progress calculation
            story_tasks: Dict[str, int] = {}
            story_completed_tasks: Dict[str, int] = {}

            # Set of completed statuses
            completed_statuses = {
                "done", "closed", "resolved", "completed"
            }

            # Set of story-like issue types
            story_types = {
                "story", "epic"
            }

            # First pass: identify stories and group tasks by story_id
            for issue in issues:
                # Add to story tasks count if it has a story_id
                if issue.story_id:
                    if issue.story_id not in story_tasks:
                        story_tasks[issue.story_id] = 0
                        story_completed_tasks[issue.story_id] = 0

                    story_tasks[issue.story_id] += 1

                    # Count completed tasks
                    if issue.status.value.lower() in completed_statuses:
                        story_completed_tasks[issue.story_id] += 1

            # Convert issues to GanttTaskResponse
            tasks: List[GanttTaskResponse] = []
            for issue in issues:
                progress = None

                # Calculate progress for stories
                if issue.type.value.lower() in story_types and issue.jira_issue_id in story_tasks:
                    total_tasks = story_tasks[issue.jira_issue_id]
                    completed_tasks = story_completed_tasks[issue.jira_issue_id]

                    if total_tasks > 0:
                        progress = (completed_tasks / total_tasks) * 100
                        log.debug(
                            f"Calculated progress for story {issue.key}: {progress}% ({completed_tasks}/{total_tasks} tasks)")

                task = GanttTaskResponse(
                    id=issue.jira_issue_id,
                    name=issue.summary,
                    assignee=issue.assignee.name if issue.assignee else None,
                    type=issue.type,
                    status=issue.status,
                    dependencies=issue.story_id,
                    plan_start=issue.planned_start_time,
                    plan_end=issue.planned_end_time,
                    actual_start=issue.actual_start_time,
                    actual_end=issue.actual_end_time,
                    progress=progress
                )
                tasks.append(task)

            return tasks

        except Exception as e:
            log.error(f"Error getting Gantt chart data: {str(e)}")
            raise
