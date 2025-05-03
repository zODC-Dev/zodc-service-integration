from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.controllers.jira_issue_controller import JiraIssueController
from src.app.dependencies.controllers import get_jira_issue_controller
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_issue import JiraIssueDescriptionDTO
from src.configs.database import get_db
from src.domain.models.apis.jira_issue_history import JiraIssueHistoryAPIGetDTO

router = APIRouter()


@router.get("/{issue_key}/changelogs", response_model=StandardResponse[JiraIssueHistoryAPIGetDTO])
async def get_issue_changelogs(
    issue_key: str,
    controller: JiraIssueController = Depends(get_jira_issue_controller),
    session: AsyncSession = Depends(get_db)
) -> StandardResponse[JiraIssueHistoryAPIGetDTO]:
    """Lấy changelog của một Jira Issue"""
    return await controller.get_issue_changelogs(session, issue_key)


@router.get("/{issue_key}/description", response_model=StandardResponse[JiraIssueDescriptionDTO])
async def get_issue_description(
    issue_key: str,
    controller: JiraIssueController = Depends(get_jira_issue_controller),
    session: AsyncSession = Depends(get_db)
) -> StandardResponse[JiraIssueDescriptionDTO]:
    """Lấy HTML description của một Jira Issue"""
    return await controller.get_issue_description(session, issue_key)
