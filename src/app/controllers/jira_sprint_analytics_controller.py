from datetime import time

from src.app.schemas.requests.gantt_chart import GanttChartRequest
from src.app.schemas.responses.gantt_chart import GanttChartFeasibilityResponse, GanttChartResponse
from src.app.schemas.responses.jira_sprint_analytics import SprintBurndownResponse, SprintBurnupResponse
from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.app.services.jira_sprint_analytics_service import JiraSprintAnalyticsApplicationService
from src.configs.logger import log
from src.domain.models.gantt_chart import ScheduleConfigModel


class JiraSprintAnalyticsController:
    """Controller for Sprint Analytics APIs"""

    def __init__(self, sprint_analytics_service: JiraSprintAnalyticsApplicationService, gantt_chart_service: GanttChartApplicationService = None):
        self.sprint_analytics_service = sprint_analytics_service
        self.gantt_chart_service = gantt_chart_service

    async def get_sprint_burndown_chart(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> SprintBurndownResponse:
        """Get burndown chart data for a sprint"""
        return await self.sprint_analytics_service.get_sprint_burndown_chart(
            user_id=user_id,
            project_key=project_key,
            sprint_id=sprint_id
        )

    async def get_sprint_burnup_chart(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> SprintBurnupResponse:
        """Get burnup chart data for a sprint"""
        return await self.sprint_analytics_service.get_sprint_burnup_chart(
            user_id=user_id,
            project_key=project_key,
            sprint_id=sprint_id
        )

    async def get_sprint_gantt_chart(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int,
        params: GanttChartRequest
    ) -> GanttChartResponse:
        """Get Gantt chart for a sprint"""
        try:
            # Create config from params
            config = ScheduleConfigModel(
                working_hours_per_day=params.working_hours_per_day,
                hours_per_point=params.hours_per_point,
                start_work_hour=time(9, 0),
                end_work_hour=time(17, 30),
                lunch_break_minutes=params.lunch_break_minutes,
                include_weekends=params.include_weekends
            )

            # Get Gantt chart from service
            gantt_chart = await self.gantt_chart_service.get_gantt_chart(
                project_key=project_key,
                sprint_id=sprint_id,
                config=config,
                workflow_id=params.workflow_id
            )

            # Convert to API response format
            tasks_response = []
            for task in gantt_chart.tasks:
                tasks_response.append({
                    "id": task.jira_key or task.node_id,
                    "text": task.title,
                    "start_date": task.plan_start_time,
                    "end_date": task.plan_end_time,
                    "progress": 0,
                    "type": task.type,
                    "estimate_points": task.estimate_points,
                    "estimate_hours": task.estimate_hours,
                    "assignee": task.assignee_name,
                    "predecessors": task.predecessors
                })

            response = GanttChartResponse(
                project_key=project_key,
                sprint_id=sprint_id,
                sprint_name=gantt_chart.sprint_name or f"Sprint {sprint_id}",
                sprint_start_date=gantt_chart.start_date,
                sprint_end_date=gantt_chart.end_date,
                tasks=tasks_response,
                is_feasible=gantt_chart.is_feasible,
                working_hours_per_day=config.working_hours_per_day,
                hours_per_point=config.hours_per_point
            )

            return response

        except Exception as e:
            log.error(f"Error generating Gantt chart: {str(e)}")
            raise

    async def check_sprint_feasibility(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int,
        params: GanttChartRequest
    ) -> GanttChartFeasibilityResponse:
        """Check if a sprint is feasible"""
        try:
            # Create config from params
            config = ScheduleConfigModel(
                working_hours_per_day=params.working_hours_per_day,
                hours_per_point=params.hours_per_point,
                start_work_hour=time(9, 0),
                end_work_hour=time(17, 30),
                lunch_break_minutes=params.lunch_break_minutes,
                include_weekends=params.include_weekends
            )

            # Get Gantt chart from service
            gantt_chart = await self.gantt_chart_service.get_gantt_chart(
                project_key=project_key,
                sprint_id=sprint_id,
                config=config,
                workflow_id=params.workflow_id
            )

            # Calculate total points and hours
            total_points = sum(task.estimate_points for task in gantt_chart.tasks)
            total_hours = sum(task.estimate_hours for task in gantt_chart.tasks)

            # Get the last task end time
            last_end_time = max(
                (task.plan_end_time for task in gantt_chart.tasks),
                default=gantt_chart.start_date
            )

            return GanttChartFeasibilityResponse(
                is_feasible=gantt_chart.is_feasible,
                total_points=total_points,
                total_hours=total_hours,
                sprint_start_date=gantt_chart.start_date,
                sprint_end_date=gantt_chart.end_date,
                expected_completion_date=last_end_time,
                task_count=len(gantt_chart.tasks)
            )

        except Exception as e:
            log.error(f"Error checking sprint feasibility: {str(e)}")
            raise
