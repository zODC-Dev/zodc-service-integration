from typing import Any, Dict

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.logger import log
from src.domain.constants.jira import JiraActionType
from src.domain.models.nats.replies.jira_issue import (
    JiraIssueBatchLinkNATSReplyDTO,
    JiraIssueSyncNATSReplyDTO,
)
from src.domain.models.nats.requests.jira_issue import JiraIssueBatchLinkNATSRequestDTO
from src.domain.services.nats_message_handler import INATSRequestHandler


class JiraIssueLinkRequestHandler(INATSRequestHandler):
    def __init__(self, jira_issue_service: JiraIssueApplicationService):
        self.jira_issue_service = jira_issue_service

    async def handle(self, subject: str, message: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
        """Xử lý yêu cầu liên kết các issue Jira

        Args:
            subject: The NATS message subject
            message: The message payload
            session: The database session to use for operations

        Returns:
            A dictionary with the result of the operation
        """
        try:
            # Chuyển đổi raw message thành DTO
            request = JiraIssueBatchLinkNATSRequestDTO.model_validate(message)

            log.info(f"Đã nhận yêu cầu liên kết issue Jira: {request}")

            # Xử lý yêu cầu liên kết, passing the session
            results = await self.jira_issue_service.handle_link_request(session, request)

            # Trả về kết quả
            response = JiraIssueBatchLinkNATSReplyDTO(results=results)
            return response.model_dump()

        except Exception as e:
            log.error(f"Lỗi khi xử lý yêu cầu liên kết issue Jira: {str(e)}")
            error_response = JiraIssueBatchLinkNATSReplyDTO(
                results=[
                    JiraIssueSyncNATSReplyDTO(
                        success=False,
                        action_type=JiraActionType.UPDATE,  # Sử dụng UPDATE vì chúng ta không có LINK
                        error_message=f"Lỗi xử lý batch: {str(e)}"
                    )
                ]
            )
            return error_response.model_dump()
