from typing import List

from src.app.schemas.responses.jira_sprint_analytics import (
    SprintBurndownResponse,
    SprintBurnupResponse,
    SprintGoalResponse,
    TaskReportResponse,
)
from src.configs.logger import log
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

            # Chuyển đổi domain model sang response DTO với các giá trị đã làm tròn
            return SprintBurndownResponse(
                sprint_name=burndown_data.name,
                start_date=burndown_data.start_date.strftime("%Y-%m-%d"),
                end_date=burndown_data.end_date.strftime("%Y-%m-%d"),
                total_points_initial=round(burndown_data.total_points_initial, 2),
                total_points_current=round(burndown_data.total_points_current, 2),
                dates=burndown_data.get_dates_list(),
                ideal_burndown=self._round_float_list(burndown_data.get_ideal_burndown()),
                actual_burndown=self._round_float_list(burndown_data.get_actual_burndown()),
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

            # Chuyển đổi domain model sang response DTO với các giá trị đã làm tròn
            return SprintBurnupResponse(
                sprint_name=burnup_data.name,
                start_date=burnup_data.start_date.strftime("%Y-%m-%d"),
                end_date=burnup_data.end_date.strftime("%Y-%m-%d"),
                total_points_initial=round(burnup_data.total_points_initial, 2),
                total_points_current=round(burnup_data.total_points_current, 2),
                dates=burnup_data.get_dates_list(),
                ideal_burnup=self._round_float_list(ideal_burnup),
                actual_burnup=self._round_float_list(burnup_data.get_actual_burnup()),
                scope_line=self._round_float_list(burnup_data.get_scope_line()),
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
                completedTasks=TaskReportResponse(
                    numberOfTasks=goal_data.completed_tasks.number_of_tasks,
                    percentage=goal_data.completed_tasks.percentage,
                    points=goal_data.completed_tasks.points
                ),
                inProgressTasks=TaskReportResponse(
                    numberOfTasks=goal_data.in_progress_tasks.number_of_tasks,
                    percentage=goal_data.in_progress_tasks.percentage,
                    points=goal_data.in_progress_tasks.points
                ),
                toDoTasks=TaskReportResponse(
                    numberOfTasks=goal_data.to_do_tasks.number_of_tasks,
                    percentage=goal_data.to_do_tasks.percentage,
                    points=goal_data.to_do_tasks.points
                ),
                addedPoints=goal_data.added_points,
                totalPoints=goal_data.total_points
            )
        except Exception as e:
            log.error(f"Error getting sprint goal: {str(e)}")
            raise
