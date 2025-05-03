from typing import List

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_issue import (
    JiraIssueCommentAPICreateDTO,
    JiraIssueCommentAPIGetDTO,
    JiraIssueDescriptionAPIGetDTO,
)
from src.app.services.jira_issue_history_service import JiraIssueHistoryApplicationService
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.domain.exceptions.jira_exceptions import JiraIssueNotFoundError
from src.domain.models.apis.jira_issue_history import JiraIssueHistoryAPIGetDTO


class JiraIssueController:
    def __init__(
        self,
        jira_issue_service: JiraIssueApplicationService,
        jira_issue_history_service: JiraIssueHistoryApplicationService,
    ):
        self.jira_issue_service = jira_issue_service
        self.jira_issue_history_service = jira_issue_history_service

    async def get_issue_changelogs(self, session: AsyncSession, issue_key: str) -> StandardResponse[JiraIssueHistoryAPIGetDTO]:
        """Lấy changelog của một Jira Issue

        Args:
            session: AsyncSession
            issue_key: Key của Jira Issue

        Returns:
            Lịch sử thay đổi của issue
        """
        try:
            result = await self.jira_issue_history_service.get_issue_changelogs(session, issue_key)
            return StandardResponse(
                message="Successfully fetched changelogs",
                data=result
            )
        except JiraIssueNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_issue_description(self, session: AsyncSession, issue_key: str) -> StandardResponse[JiraIssueDescriptionAPIGetDTO]:
        """Lấy description (HTML) của một Jira Issue

        Args:
            session: AsyncSession
            issue_key: Key của Jira Issue

        Returns:
            HTML description của issue
        """
        try:
            result = await self.jira_issue_service.get_issue_description_html(session, issue_key)
            return StandardResponse(
                message="Successfully fetched issue description",
                data=result
            )
        except JiraIssueNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_issue_comments(self, session: AsyncSession, issue_key: str) -> StandardResponse[List[JiraIssueCommentAPIGetDTO]]:
        """Lấy comments của một Jira Issue

        Args:
            session: AsyncSession
            issue_key: Key của Jira Issue

        Returns:
            Comments của issue
        """
        try:
            result = await self.jira_issue_service.get_issue_comments(session, issue_key)

            # Convert to DTOs
            dto_result = [JiraIssueCommentAPIGetDTO.from_domain(comment) for comment in result]

            return StandardResponse(
                message="Successfully fetched issue comments",
                data=dto_result
            )
        except JiraIssueNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

    async def create_issue_comment(self, session: AsyncSession, user_id: int, issue_key: str, comment: JiraIssueCommentAPICreateDTO) -> StandardResponse[JiraIssueCommentAPIGetDTO]:
        """Tạo comment cho một Jira Issue

        Args:
            session: AsyncSession
            user_id: ID của user
            issue_key: Key của Jira Issue
            comment: Comment cần tạo

        Returns:
            Comment đã tạo
        """
        try:
            result = await self.jira_issue_service.create_issue_comment(session, user_id, issue_key, comment.content)
            return StandardResponse(
                message="Successfully created issue comment",
                data=result
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
