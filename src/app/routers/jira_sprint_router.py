from fastapi import APIRouter, Depends, Path, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.controllers.jira_sprint_controller import JiraSprintController
from src.app.dependencies.controllers import get_jira_sprint_controller
from src.app.schemas.requests.jira_sprint import SprintStartRequest
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_project import GetJiraSprintDetailsResponse, GetJiraSprintResponse
from src.configs.database import get_db

router = APIRouter()


@router.get("/current", response_model=StandardResponse[GetJiraSprintResponse])
async def get_current_sprint(
    controller: JiraSprintController = Depends(get_jira_sprint_controller),
    project_key: str = Query(..., description="Key of the project to get current sprint", alias="projectKey"),
    session: AsyncSession = Depends(get_db)
) -> StandardResponse[GetJiraSprintResponse]:
    """Get the current sprint in Jira"""
    return await controller.get_current_sprint(session=session, project_key=project_key)


@router.get("/{sprint_id}", response_model=StandardResponse[GetJiraSprintDetailsResponse])
async def get_sprint_by_id(
    sprint_id: int = Path(..., description="ID of the sprint to retrieve"),
    controller: JiraSprintController = Depends(get_jira_sprint_controller),
    session: AsyncSession = Depends(get_db)
) -> StandardResponse[GetJiraSprintDetailsResponse]:
    """Get detailed sprint information by ID.

    Returns:
    - Sprint details including start date, end date, and goal
    - Number of tasks by status (to do, in progress, done)
    - Complete date if the sprint is completed
    """
    return await controller.get_sprint_by_id(session=session, sprint_id=sprint_id)


@router.post("/{sprint_id}/start", response_model=StandardResponse[GetJiraSprintResponse])
async def start_sprint(
    sprint_data: SprintStartRequest,
    sprint_id: int = Path(..., description="ID of the sprint to start"),
    controller: JiraSprintController = Depends(get_jira_sprint_controller),
    session: AsyncSession = Depends(get_db)
) -> StandardResponse[GetJiraSprintResponse]:
    """Start a sprint in Jira using admin account

    Parameters:
    - sprint_id: ID of the sprint to start
    - start_date: Optional start date (default: current date)
    - end_date: Optional end date (default: start_date + 14 days)
    - goal: Optional sprint goal
    """
    return await controller.start_sprint(session=session, sprint_id=sprint_id, sprint_data=sprint_data)


@router.post("/{sprint_id}/end", response_model=StandardResponse[GetJiraSprintResponse])
async def end_sprint(
    sprint_id: int = Path(..., description="ID of the sprint to end"),
    controller: JiraSprintController = Depends(get_jira_sprint_controller),
    session: AsyncSession = Depends(get_db)
) -> StandardResponse[GetJiraSprintResponse]:
    """End a sprint in Jira using admin account"""
    return await controller.end_sprint(session=session, sprint_id=sprint_id)
