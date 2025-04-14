from fastapi import APIRouter, Depends

from src.app.controllers.jira_issue_controller import JiraIssueController
from src.app.dependencies.controllers import get_jira_issue_controller
from src.app.schemas.responses.base import StandardResponse
from src.domain.models.apis.jira_issue_history import JiraIssueHistoryAPIGetDTO

router = APIRouter()


@router.get("/{issue_key}/changelogs", response_model=StandardResponse[JiraIssueHistoryAPIGetDTO])
async def get_issue_changelogs(
    issue_key: str,
    controller: JiraIssueController = Depends(get_jira_issue_controller),
) -> StandardResponse[JiraIssueHistoryAPIGetDTO]:
    """Lấy changelog của một Jira Issue"""
    return await controller.get_issue_changelogs(issue_key)
