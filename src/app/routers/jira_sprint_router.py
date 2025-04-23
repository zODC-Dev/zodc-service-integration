from fastapi import APIRouter, Depends, Path

from src.app.controllers.jira_sprint_controller import JiraSprintController
from src.app.dependencies.controllers import get_jira_sprint_controller
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_project import GetJiraSprintDetailsResponse, GetJiraSprintResponse

router = APIRouter()


@router.get("/{sprint_id}", response_model=StandardResponse[GetJiraSprintDetailsResponse])
async def get_sprint_by_id(
    sprint_id: int = Path(..., description="ID of the sprint to retrieve"),
    controller: JiraSprintController = Depends(get_jira_sprint_controller)
) -> StandardResponse[GetJiraSprintDetailsResponse]:
    """Get detailed sprint information by ID.

    Returns:
    - Sprint details including start date, end date, and goal
    - Number of tasks by status (to do, in progress, done)
    - Complete date if the sprint is completed
    """
    return await controller.get_sprint_by_id(sprint_id=sprint_id)


@router.post("/{sprint_id}/start", response_model=StandardResponse[GetJiraSprintResponse])
async def start_sprint(
    sprint_id: int = Path(..., description="ID of the sprint to start"),
    controller: JiraSprintController = Depends(get_jira_sprint_controller)
) -> StandardResponse[GetJiraSprintResponse]:
    """Start a sprint in Jira using admin account"""
    return await controller.start_sprint(sprint_id=sprint_id)


@router.post("/{sprint_id}/end", response_model=StandardResponse[GetJiraSprintResponse])
async def end_sprint(
    sprint_id: int = Path(..., description="ID of the sprint to end"),
    controller: JiraSprintController = Depends(get_jira_sprint_controller)
) -> StandardResponse[GetJiraSprintResponse]:
    """End a sprint in Jira using admin account"""
    return await controller.end_sprint(sprint_id=sprint_id)
