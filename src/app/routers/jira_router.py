from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from src.app.controllers.jira_controller import JiraController
from src.app.dependencies.auth import get_jwt_claims
from src.app.dependencies.jira import get_jira_controller
from src.app.schemas.requests.auth import JWTClaims
from src.app.schemas.requests.jira import JiraIssueCreateRequest, JiraIssueUpdateRequest
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira import (
    JiraCreateIssueResponse,
    JiraIssueResponse,
    JiraProjectResponse,
    JiraSprintResponse,
)
from src.domain.constants.jira import JiraIssueType

router = APIRouter()


@router.get("/projects/{project_key}/issues", response_model=StandardResponse[List[JiraIssueResponse]])
async def get_project_issues(
    project_key: str,
    claims: JWTClaims = Depends(get_jwt_claims),
    sprint_id: Optional[str] = Query(
        None, alias="sprintId", description="Filter by sprint number (use 'backlog' for backlog items)"),
    issue_type: Optional[JiraIssueType] = Query(
        None, alias="issueType", description="Filter by issue type (Bug, Task, Story, Epic)"),
    search: Optional[str] = Query(None, alias="search", description="Search in issue summary and description"),
    limit: int = Query(50, ge=1, le=100),
    controller: JiraController = Depends(get_jira_controller),
) -> StandardResponse[List[JiraIssueResponse]]:
    """Get issues from a specific Jira project"""
    is_backlog = None
    if sprint_id == "backlog":
        is_backlog = True
        sprint_id = None

    return await controller.get_project_issues(
        user_id=int(claims.sub),
        project_key=project_key,
        sprint_id=sprint_id,
        is_backlog=is_backlog,
        issue_type=issue_type,
        search=search,
        limit=limit
    )


@router.get("/projects", response_model=StandardResponse[List[JiraProjectResponse]])
async def get_accessible_projects(
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraController = Depends(get_jira_controller)
) -> StandardResponse[List[JiraProjectResponse]]:
    """Get all Jira projects that the user has access to"""
    user_id = int(claims.sub)
    return await controller.get_accessible_projects(user_id)


@router.post("/issues", response_model=StandardResponse[JiraCreateIssueResponse])
async def create_issue(
    issue: JiraIssueCreateRequest,
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraController = Depends(get_jira_controller),
) -> StandardResponse[JiraCreateIssueResponse]:
    """Create a new Jira issue"""
    user_id = int(claims.sub)
    return await controller.create_issue(user_id, issue)


@router.patch("/issues/{issue_id}", response_model=StandardResponse[JiraIssueResponse])
async def update_issue(
    issue_id: str,
    update: JiraIssueUpdateRequest,
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraController = Depends(get_jira_controller),
) -> StandardResponse[JiraIssueResponse]:
    """Update a Jira issue"""
    user_id = int(claims.sub)
    return await controller.update_issue(user_id, issue_id, update)


@router.get("/projects/{project_key}/sprints", response_model=StandardResponse[List[JiraSprintResponse]])
async def get_project_sprints(
    project_key: str,
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraController = Depends(get_jira_controller),
) -> StandardResponse[List[JiraSprintResponse]]:
    """Get all sprints from a specific Jira project"""
    user_id = int(claims.sub)

    return await controller.get_project_sprints(
        user_id=user_id,
        project_id=project_key
    )
