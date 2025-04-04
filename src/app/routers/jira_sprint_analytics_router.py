from fastapi import APIRouter, Depends, Path

from src.app.controllers.jira_sprint_analytics_controller import JiraSprintAnalyticsController
from src.app.dependencies.auth import get_jwt_claims
from src.app.dependencies.jira_sprint_analytics import get_sprint_analytics_controller
from src.app.schemas.requests.auth import JWTClaims
from src.app.schemas.responses.jira_sprint_analytics import SprintBurndownResponse, SprintBurnupResponse

router = APIRouter()


@router.get(
    "/{project_key}/sprints/{sprint_id}/analytics/burndown",
    response_model=SprintBurndownResponse,
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
    response_model=SprintBurnupResponse,
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
