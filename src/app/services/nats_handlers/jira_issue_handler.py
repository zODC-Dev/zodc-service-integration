from typing import Any, Dict

from src.app.dtos.jira.jira_sync_dto import (
    JiraBatchSyncRequestDTO,
    JiraBatchSyncResponseDTO,
    JiraIssueSyncRequestDTO,
    JiraIssueSyncResponseDTO,
)
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.logger import log
from src.domain.constants.jira import JiraActionType
from src.domain.services.nats_message_handler import INATSMessageHandler, INATSRequestHandler

# class INATSMessageHandler(ABC):
#     """Base interface for NATS message handlers"""
#     @abstractmethod
#     async def handle(self, subject: str, message: Dict[str, Any]) -> None:
#         pass


# class INATSRequestHandler(ABC):
#     """Base interface for NATS request-reply handlers"""
#     @abstractmethod
#     async def handle(self, subject: str, message: Dict[str, Any]) -> Dict[str, Any]:
#         pass


class JiraIssueMessageHandler(INATSMessageHandler):
    def __init__(self, jira_issue_service: JiraIssueApplicationService):
        self.jira_issue_service = jira_issue_service

    async def handle(self, subject: str, message: Dict[str, Any]) -> None:
        """Handle Jira issue update messages"""
        try:
            # Convert raw message to DTO
            request = JiraIssueSyncRequestDTO(**message)

            # Delegate to service
            await self.jira_issue_service.handle_update_request(request)

        except Exception as e:
            log.error(f"Error handling Jira issue message: {str(e)}")

            issue_id: str = message.get("issue_id")

            # Publish error event if needed
            await self.jira_issue_service.publish_update_error(
                issue_id=issue_id,
                error=str(e)
            )


class JiraIssueSyncRequestHandler(INATSRequestHandler):
    def __init__(self, jira_issue_service: JiraIssueApplicationService):
        self.jira_issue_service = jira_issue_service

    async def handle(self, subject: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Jira issue sync requests"""
        try:
            # Convert raw message to DTO
            request = JiraBatchSyncRequestDTO(
                issues=[JiraIssueSyncRequestDTO(**item) for item in message]
            )

            # Process sync request
            results = await self.jira_issue_service.handle_sync_request(request)

            # Return response
            response = JiraBatchSyncResponseDTO(results=results)
            return response.model_dump()

        except Exception as e:
            log.error(f"Error handling Jira sync request: {str(e)}")
            error_response = JiraBatchSyncResponseDTO(
                results=[
                    JiraIssueSyncResponseDTO(
                        success=False,
                        action_type=JiraActionType.CREATE,
                        error_message=f"Batch processing error: {str(e)}"
                    )
                ]
            )
            return error_response.model_dump()
