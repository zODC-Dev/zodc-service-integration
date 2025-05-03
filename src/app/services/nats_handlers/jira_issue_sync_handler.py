from typing import Any, Dict

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.logger import log
from src.domain.constants.jira import JiraActionType
from src.domain.models.nats.replies.jira_issue import JiraIssueBatchSyncNATSReplyDTO, JiraIssueSyncNATSReplyDTO
from src.domain.models.nats.requests.jira_issue import JiraIssueBatchSyncNATSRequestDTO
from src.domain.services.nats_message_handler import INATSRequestHandler


class JiraIssueSyncRequestHandler(INATSRequestHandler):
    def __init__(self, jira_issue_service: JiraIssueApplicationService):
        self.jira_issue_service = jira_issue_service

    async def handle(self, subject: str, message: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
        """Handle Jira issue sync requests

        Args:
            subject: The NATS message subject
            message: The message payload
            session: The database session to use for operations

        Returns:
            A dictionary with the result of the operation
        """
        try:
            # Convert raw message to DTO
            request = JiraIssueBatchSyncNATSRequestDTO.model_validate(message)

            log.info(f"Received Jira issue sync request: {request}")

            # Process sync request using the provided session
            results = await self.jira_issue_service.handle_sync_request(session, request)

            # Return response
            response = JiraIssueBatchSyncNATSReplyDTO(results=results)
            return response.model_dump()

        except Exception as e:
            log.error(f"Error handling Jira sync request: {str(e)}")
            error_response = JiraIssueBatchSyncNATSReplyDTO(
                results=[
                    JiraIssueSyncNATSReplyDTO(
                        success=False,
                        action_type=JiraActionType.CREATE,
                        error_message=f"Batch processing error: {str(e)}"
                    )
                ]
            )
            return error_response.model_dump()
