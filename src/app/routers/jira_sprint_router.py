from fastapi import APIRouter, Depends, Path

from src.app.controllers.jira_sprint_controller import JiraSprintController
from src.app.dependencies.controllers import get_jira_sprint_controller
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_project import GetJiraSprintResponse

router = APIRouter()


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
