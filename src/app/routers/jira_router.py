from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from src.domain.constants.jira import JiraIssueType
from src.app.controllers.jira_controller import JiraController
from src.app.dependencies.jira import get_jira_controller
from src.app.schemas.requests.jira import JiraIssueCreateRequest, JiraIssueGetRequest, JiraIssueUpdateRequest
from src.app.schemas.responses.jira import JiraCreateIssueResponse, JiraProjectResponse, JiraIssueResponse, JiraSprintResponse

router = APIRouter()


@router.get("/projects/{project_id}/issues", response_model=List[JiraIssueResponse])
async def get_project_issues(
    request: JiraIssueGetRequest,
    controller: JiraController = Depends(get_jira_controller),
) -> List[JiraIssueResponse]:
    """Get issues from a specific Jira project"""
    is_backlog = None
    if request.sprint_id == "backlog":
        is_backlog = True
        sprint_id = None

    return await controller.get_project_issues(
        user_id=request.user_id,
        project_id=request.project_key,
        sprint_id=sprint_id,
        is_backlog=is_backlog,
        issue_type=request.issue_type,
        limit=request.limit
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


@router.patch("/issues/{issue_id}", response_model=JiraIssueResponse)
async def update_issue(
    issue_id: str,
    user_id: int,
    update: JiraIssueUpdateRequest,
    controller: JiraController = Depends(get_jira_controller),
) -> JiraIssueResponse:
    """Update a Jira issue"""
    return await controller.update_issue(user_id, issue_id, update)


@router.get("/projects/{project_id}/sprints", response_model=List[JiraSprintResponse])
async def get_project_sprints(
    project_id: str,
    user_id: int,
    controller: JiraController = Depends(get_jira_controller),
) -> List[JiraSprintResponse]:
    """Get all sprints from a specific Jira project"""
    return await controller.get_project_sprints(
        user_id=user_id,
        project_id=project_id
    )
