from typing import List

from fastapi import APIRouter, Depends, Path

from src.app.controllers.jira_sprint_analytics_controller import JiraSprintAnalyticsController
from src.app.dependencies.auth import get_jwt_claims
from src.app.dependencies.controllers import get_sprint_analytics_controller
from src.app.schemas.requests.auth import JWTClaims
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.gantt_chart import GanttChartResponse
from src.app.schemas.responses.jira_sprint_analytics import (
    BugReportDataResponse,
    SprintBurndownResponse,
    SprintBurnupResponse,
    SprintGoalResponse,
    WorkloadResponse,
)

router = APIRouter()


@router.get(
    "/{project_key}/sprints/{sprint_id}/analytics/burndown",
    response_model=StandardResponse[SprintBurndownResponse],
    summary="Get burndown chart data for a sprint",
    description="Returns data needed for rendering a sprint burndown chart"
)
async def get_sprint_burndown_chart(
    project_key: str = Path(..., description="Project key"),
    sprint_id: int = Path(..., description="Sprint ID"),
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraSprintAnalyticsController = Depends(get_sprint_analytics_controller)
):
    """Get burndown chart data for a sprint"""
    return await controller.get_sprint_burndown_chart(
        user_id=int(claims.sub),
        project_key=project_key,
        sprint_id=sprint_id
    )


@router.get(
    "/{project_key}/sprints/{sprint_id}/analytics/burnup",
    response_model=StandardResponse[SprintBurnupResponse],
    summary="Get burnup chart data for a sprint",
    description="Returns data needed for rendering a sprint burnup chart"
)
async def get_sprint_burnup_chart(
    project_key: str = Path(..., description="Project key"),
    sprint_id: int = Path(..., description="Sprint ID"),
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraSprintAnalyticsController = Depends(get_sprint_analytics_controller)
):
    """Get burnup chart data for a sprint"""
    return await controller.get_sprint_burnup_chart(
        user_id=int(claims.sub),
        project_key=project_key,
        sprint_id=sprint_id
    )


@router.get(
    "/{project_key}/sprints/{sprint_id}/analytics/goal",
    response_model=StandardResponse[SprintGoalResponse],
    summary="Get sprint goal data for a sprint",
    description="Returns data about sprint goals, task completion status, and points"
)
async def get_sprint_goal(
    project_key: str = Path(..., description="Project key"),
    sprint_id: int = Path(..., description="Sprint ID"),
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraSprintAnalyticsController = Depends(get_sprint_analytics_controller)
):
    """Get sprint goal data for a sprint"""
    return await controller.get_sprint_goal(
        user_id=int(claims.sub),
        project_key=project_key,
        sprint_id=sprint_id
    )


@router.get(
    "/{project_key}/sprints/{sprint_id}/analytics/bugs",
    response_model=StandardResponse[BugReportDataResponse],
    summary="Get bug report data for a sprint",
    description="Returns data about bugs in the sprint, including priority distribution and details"
)
async def get_bug_report(
    project_key: str = Path(..., description="Project key"),
    sprint_id: int = Path(..., description="Sprint ID"),
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraSprintAnalyticsController = Depends(get_sprint_analytics_controller)
):
    """Get bug report data for a sprint"""
    return await controller.get_bug_report(
        user_id=int(claims.sub),
        project_key=project_key,
        sprint_id=sprint_id
    )


@router.get(
    "/{project_key}/sprints/{sprint_id}/analytics/workload",
    response_model=StandardResponse[List[WorkloadResponse]],
    summary="Get workload data for team members in a sprint",
    description="Returns data about workload distribution among team members, including completed and remaining points"
)
async def get_team_workload(
    project_key: str = Path(..., description="Project key"),
    sprint_id: int = Path(..., description="Sprint ID"),
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraSprintAnalyticsController = Depends(get_sprint_analytics_controller)
):
    """Get workload data for team members in a sprint"""
    return await controller.get_team_workload(
        user_id=int(claims.sub),
        project_key=project_key,
        sprint_id=sprint_id
    )


@router.get(
    "/{project_key}/sprints/{sprint_id}/analytics/gantt",
    response_model=GanttChartResponse,
    summary="Get Gantt chart data for a sprint",
    description="Returns data needed for rendering a Gantt chart, including tasks, dependencies, and schedule information"
)
async def get_gantt_chart_data(
    project_key: str = Path(..., description="Project key"),
    sprint_id: int = Path(..., description="Sprint ID"),
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraSprintAnalyticsController = Depends(get_sprint_analytics_controller)
):
    """Get Gantt chart data for a sprint"""
    return await controller.get_gantt_chart_data(
        user_id=int(claims.sub),
        project_key=project_key,
        sprint_id=sprint_id
    )
