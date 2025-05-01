from typing import List

from fastapi import HTTPException

from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.gantt_chart import GanttTaskResponse
from src.app.schemas.responses.jira_sprint_analytics import (
    BugReportDataResponse,
    SprintBurndownResponse,
    SprintBurnupResponse,
    SprintGoalResponse,
    WorkloadResponse,
)
from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.app.services.jira_sprint_analytics_service import JiraSprintAnalyticsApplicationService
from src.configs.logger import log


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
    ) -> StandardResponse[SprintBurndownResponse]:
        """Get burndown chart data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_sprint_burndown_chart(
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Sprint burndown chart data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting sprint burndown chart: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting sprint burndown chart: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_sprint_burnup_chart(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> StandardResponse[SprintBurnupResponse]:
        """Get burnup chart data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_sprint_burnup_chart(
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Sprint burnup chart data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting sprint burnup chart: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting sprint burnup chart: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_sprint_goal(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> StandardResponse[SprintGoalResponse]:
        """Get sprint goal data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_sprint_goal(
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Sprint goal data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting sprint goal: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting sprint goal: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_bug_report(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int,
    ) -> StandardResponse[BugReportDataResponse]:
        """Get bug report data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_bug_report(
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Bug report data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting bug report: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting bug report: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_team_workload(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> StandardResponse[List[WorkloadResponse]]:
        """Get workload data for team members in a sprint"""
        try:
            result = await self.sprint_analytics_service.get_team_workload(
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Team workload data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting team workload: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting team workload: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_gantt_chart_data(
        self,
        user_id: int,
        project_key: str,
        sprint_id: int
    ) -> StandardResponse[List[GanttTaskResponse]]:
        """Get Gantt chart data for a sprint"""
        try:
            result = await self.sprint_analytics_service.get_gantt_chart_data(
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id
            )
            return StandardResponse(
                data=result,
                message="Gantt chart data retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Error getting Gantt chart data: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Error getting Gantt chart data: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e
