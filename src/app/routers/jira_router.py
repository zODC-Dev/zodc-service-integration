from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request

from src.domain.constants.jira import JiraIssueType
from src.app.controllers.jira_controller import JiraController
from src.app.dependencies.jira import get_jira_controller
from src.app.schemas.requests.jira import JiraIssueCreateRequest, JiraIssueGetRequest, JiraIssueUpdateRequest
from src.app.schemas.responses.jira import JiraCreateIssueResponse, JiraProjectResponse, JiraIssueResponse, JiraSprintResponse
from src.configs.logger import log

router = APIRouter()


@router.get("/projects/{project_key}/issues", response_model=List[JiraIssueResponse])
async def get_project_issues(
    request: Request,
    project_key: str,
    sprint_id: Optional[str] = Query(
        None, alias="sprintId", description="Filter by sprint number (use 'backlog' for backlog items)"),
    issue_type: Optional[JiraIssueType] = Query(
        None, alias="issueType", description="Filter by issue type (Bug, Task, Story, Epic)"),
    search: Optional[str] = Query(None, alias="search", description="Search in issue summary and description"),
    limit: int = Query(50, ge=1, le=100),
    controller: JiraController = Depends(get_jira_controller),
) -> List[JiraIssueResponse]:
    """Get issues from a specific Jira project"""
    user_id = request.headers.get("x-kong-jwt-claim-sub")
    log.info(f"Request headers: {request.headers}")
    is_backlog = None
    if sprint_id == "backlog":
        is_backlog = True
        sprint_id = None

    return await controller.get_project_issues(
        user_id=user_id,
        project_key=project_key,
        sprint_id=sprint_id,
        is_backlog=is_backlog,
        issue_type=issue_type,
        search=search,
        limit=limit
    )


@router.get("/projects", response_model=List[JiraProjectResponse])
async def get_accessible_projects(
    request: Request,
    controller: JiraController = Depends(get_jira_controller)
) -> List[JiraProjectResponse]:
    """Get all Jira projects that the user has access to"""
    user_id = request.headers.get("x-kong-jwt-claim-sub")
    projects = await controller.get_accessible_projects(user_id)
    return projects


@router.post("/issues", response_model=JiraCreateIssueResponse)
async def create_issue(
    request: Request,
    issue: JiraIssueCreateRequest,
    controller: JiraController = Depends(get_jira_controller),
) -> JiraCreateIssueResponse:
    """Create a new Jira issue"""
    user_id = request.headers.get("x-kong-jwt-claim-sub")
    return await controller.create_issue(user_id, issue)


@router.patch("/issues/{issue_id}", response_model=JiraIssueResponse)
async def update_issue(
    request: Request,
    issue_id: str,
    update: JiraIssueUpdateRequest,
    controller: JiraController = Depends(get_jira_controller),
) -> JiraIssueResponse:
    """Update a Jira issue"""
    user_id = request.headers.get("x-kong-jwt-claim-sub")
    return await controller.update_issue(user_id, issue_id, update)


@router.get("/projects/{project_key}/sprints", response_model=List[JiraSprintResponse])
async def get_project_sprints(
    request: Request,
    project_key: str,
    controller: JiraController = Depends(get_jira_controller),
) -> List[JiraSprintResponse]:
    """Get all sprints from a specific Jira project"""
    user_id = request.headers.get("x-kong-jwt-claim-sub")

    log.info(f"request headers: {request.headers}")

    return await controller.get_project_sprints(
        user_id=user_id,
        project_id=project_key
    )
