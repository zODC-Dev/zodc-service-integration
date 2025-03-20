from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from src.app.controllers.jira_project_controller import JiraProjectController
from src.app.dependencies.auth import get_jwt_claims
from src.app.dependencies.jira_project import get_jira_project_controller
from src.app.schemas.requests.auth import JWTClaims
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_issue import (
    GetJiraIssueResponse,
)
from src.app.schemas.responses.jira_project import (
    GetJiraProjectResponse,
    GetJiraSprintResponse,
)
from src.domain.constants.jira import JiraIssueType

router = APIRouter()


@router.get("/{project_key}/issues", response_model=StandardResponse[List[GetJiraIssueResponse]])
async def get_project_issues(
    project_key: str,
    claims: JWTClaims = Depends(get_jwt_claims),
    sprint_id: Optional[str] = Query(
        None, alias="sprintId", description="Filter by sprint number (use 'backlog' for backlog items)"),
    issue_type: Optional[JiraIssueType] = Query(
        None, alias="issueType", description="Filter by issue type (Bug, Task, Story, Epic)"),
    search: Optional[str] = Query(None, alias="search", description="Search in issue summary and description"),
    limit: int = Query(50, ge=1, le=100),
    controller: JiraProjectController = Depends(get_jira_project_controller),
) -> StandardResponse[List[GetJiraIssueResponse]]:
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


@router.get("", response_model=StandardResponse[List[GetJiraProjectResponse]])
async def get_projects(
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraProjectController = Depends(get_jira_project_controller)
) -> StandardResponse[List[GetJiraProjectResponse]]:
    """Get all Jira projects that the user has access to"""
    user_id = int(claims.sub)
    return await controller.get_projects(user_id)


@router.get("/{project_key}/sprints", response_model=StandardResponse[List[GetJiraSprintResponse]])
async def get_project_sprints(
    project_key: str,
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraProjectController = Depends(get_jira_project_controller),
) -> StandardResponse[List[GetJiraSprintResponse]]:
    """Get all sprints from a specific Jira project"""
    user_id = int(claims.sub)

    return await controller.get_project_sprints(
        user_id=user_id,
        project_id=project_key
    )
