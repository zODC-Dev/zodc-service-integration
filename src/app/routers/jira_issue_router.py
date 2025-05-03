from typing import List

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.controllers.jira_issue_controller import JiraIssueController
from src.app.dependencies.auth import get_jwt_claims
from src.app.dependencies.controllers import get_jira_issue_controller
from src.app.schemas.requests.auth import JWTClaims
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_issue import (
    JiraIssueCommentAPICreateDTO,
    JiraIssueCommentAPIGetDTO,
    JiraIssueDescriptionAPIGetDTO,
)
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


@router.get("/{issue_key}/description", response_model=StandardResponse[JiraIssueDescriptionAPIGetDTO])
async def get_issue_description(
    issue_key: str,
    controller: JiraIssueController = Depends(get_jira_issue_controller),
    session: AsyncSession = Depends(get_db)
) -> StandardResponse[JiraIssueDescriptionAPIGetDTO]:
    """Lấy HTML description của một Jira Issue"""
    return await controller.get_issue_description(session, issue_key)


@router.get("/{issue_key}/comments", response_model=StandardResponse[List[JiraIssueCommentAPIGetDTO]])
async def get_issue_comments(
    issue_key: str,
    controller: JiraIssueController = Depends(get_jira_issue_controller),
    session: AsyncSession = Depends(get_db),
) -> StandardResponse[List[JiraIssueCommentAPIGetDTO]]:
    """Lấy comments của một Jira Issue"""
    return await controller.get_issue_comments(session, issue_key)


@router.post("/{issue_key}/comments", response_model=StandardResponse[JiraIssueCommentAPIGetDTO])
async def create_issue_comment(
    issue_key: str,
    comment: JiraIssueCommentAPICreateDTO,
    claims: JWTClaims = Depends(get_jwt_claims),
    controller: JiraIssueController = Depends(get_jira_issue_controller),
    session: AsyncSession = Depends(get_db),
) -> StandardResponse[JiraIssueCommentAPIGetDTO]:
    """Tạo comment cho một Jira Issue"""
    user_id = int(claims.sub)
    return await controller.create_issue_comment(session, user_id, issue_key, comment)
