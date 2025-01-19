from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from src.app.controllers.jira_controller import JiraController
from src.app.dependencies.jira import get_jira_controller
from src.app.schemas.requests.jira import JiraIssueCreateRequest
from src.app.schemas.responses.jira import JiraCreateIssueResponse, JiraProjectResponse, JiraTaskResponse

router = APIRouter()


@router.get("/projects/{project_id}/tasks", response_model=List[JiraTaskResponse])
async def get_project_tasks(
    project_id: str,
    user_id: int,
    status: Optional[str] = Query(None, description="Filter tasks by status"),
    limit: int = Query(50, ge=1, le=100),
    controller: JiraController = Depends(get_jira_controller),
) -> List[JiraTaskResponse]:
    """Get tasks from a specific Jira project"""
    return await controller.get_project_tasks(
        user_id=user_id,
        project_id=project_id,
        status=status,
        limit=limit
    )


@router.get("/projects", response_model=List[JiraProjectResponse])
async def get_accessible_projects(
    user_id: int,
    controller: JiraController = Depends(get_jira_controller)
) -> List[JiraProjectResponse]:
    """Get all Jira projects that the user has access to"""
    projects = await controller.get_accessible_projects(user_id)
    return projects


@router.post("/issues", response_model=JiraCreateIssueResponse)
async def create_issue(
    user_id: int,
    issue: JiraIssueCreateRequest,
    controller: JiraController = Depends(get_jira_controller),
) -> JiraCreateIssueResponse:
    """Create a new Jira issue"""
    return await controller.create_issue(user_id, issue)
