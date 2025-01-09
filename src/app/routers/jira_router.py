from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from src.app.controllers.jira_controller import JiraController
from src.app.dependencies.jira import get_jira_controller
from src.app.middlewares.permission_middleware import require_permissions
from src.domain.entities.jira import JiraTask

router = APIRouter()


@router.get("/projects/{project_id}/tasks", response_model=List[JiraTask])
# @require_permissions(permissions=["jira.view"], scope="project")
async def get_project_tasks(
    project_id: str,
    status: Optional[str] = Query(None, description="Filter tasks by status"),
    limit: int = Query(50, ge=1, le=100),
    controller: JiraController = Depends(get_jira_controller)
) -> List[JiraTask]:
    """Get tasks from a specific Jira project"""
    return await controller.get_project_tasks(
        project_id=project_id,
        status=status,
        limit=limit
    )
