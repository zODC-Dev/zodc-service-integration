from typing import Any, Dict

from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError
from src.domain.models.nats.replies.node_status_sync import NodeStatusSyncReply
from src.domain.models.nats.requests.node_status_sync import NodeStatusSyncRequest
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.nats_message_handler import INATSRequestHandler


class NodeStatusSyncHandler(INATSRequestHandler):
    """Xử lý message đồng bộ trạng thái node từ hệ thống khác sang Jira"""

    def __init__(self, jira_issue_api_service: IJiraIssueAPIService, jira_issue_repository: IJiraIssueRepository):
        self.jira_issue_api_service = jira_issue_api_service
        self.jira_issue_repository = jira_issue_repository

    def _parse_status(self, status: str) -> JiraIssueStatus:
        """Parse status từ string sang enum JiraIssueStatus"""
        try:
            # Convert IN_PROGRESS, IN_REVIEW, DONE, TO_DO to JiraIssueStatus
            if status.lower() == "in_progress" or status.lower() == "in_process":
                return JiraIssueStatus.IN_PROGRES
            elif status.lower() == "done" or status.lower() == "completed":
                return JiraIssueStatus.DONE
            elif status.lower() == "to_do":
                return JiraIssueStatus.TO_DO
            else:
                raise ValueError(f"Invalid status: {status}")
        except ValueError as e:
            raise ValueError(f"Invalid status: {status}") from e

    async def handle(self, subject: str, message: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
        """Xử lý message đồng bộ trạng thái node

        Args:
            session: AsyncSession
            subject: Tên subject của message
            message: Dữ liệu của message

        Returns:
            Dict[str, Any]: Response trả về cho client
        """
        transaction_id = None
        try:
            # Parse dữ liệu đầu vào
            request = NodeStatusSyncRequest.model_validate(message)
            transaction_id = request.transaction_id

            # Check last synced at
            if request.last_synced_at:
                issue = await self.jira_issue_repository.get_by_jira_issue_key(session=session, jira_issue_key=request.jira_key)
                if issue and issue.last_synced_at and issue.last_synced_at > request.last_synced_at:
                    log.info(f"Issue {request.jira_key} was synced after {request.last_synced_at}, skipping")
                    return NodeStatusSyncReply(
                        success=False,
                        error_message=f"Issue {request.jira_key} was synced after {request.last_synced_at}, skipping",
                        data={"transaction_id": request.transaction_id}
                    ).model_dump()

            log.info(
                f"[NodeStatusSyncHandler] Nhận request cập nhật trạng thái, transaction_id={request.transaction_id}, jira_key={request.jira_key}, status={request.status}")

            # Cập nhật trạng thái issue trong Jira sử dụng admin auth để tránh vấn đề về quyền
            success = await self.jira_issue_api_service.transition_issue_with_admin_auth(
                issue_id=request.jira_key,
                status=self._parse_status(request.status)
            )

            if not success:
                log.error(f"[NodeStatusSyncHandler] Không thể cập nhật trạng thái cho issue {request.jira_key}")
                return NodeStatusSyncReply(
                    success=False,
                    error_message=f"Không thể cập nhật trạng thái cho issue {request.jira_key}",
                    data={"transaction_id": request.transaction_id}
                ).model_dump()

            log.info(f"[NodeStatusSyncHandler] Cập nhật trạng thái thành công cho issue {request.jira_key}")
            result = NodeStatusSyncReply(
                success=True,
                data={
                    "transaction_id": request.transaction_id,
                    "jira_key": request.jira_key,
                    "node_id": request.node_id,
                    "status": request.status
                }
            )

            return result.model_dump()

        except JiraAuthenticationError as e:
            log.error(f"[NodeStatusSyncHandler] Lỗi xác thực Jira: {str(e)}, transaction_id={transaction_id}")
            return NodeStatusSyncReply(
                success=False,
                error_message=f"Lỗi xác thực Jira: {str(e)}",
                data={"transaction_id": transaction_id}
            ).model_dump()

        except JiraConnectionError as e:
            log.error(f"[NodeStatusSyncHandler] Lỗi kết nối Jira: {str(e)}, transaction_id={transaction_id}")
            return NodeStatusSyncReply(
                success=False,
                error_message=f"Lỗi kết nối Jira: {str(e)}",
                data={"transaction_id": transaction_id}
            ).model_dump()

        except JiraRequestError as e:
            log.error(f"[NodeStatusSyncHandler] Lỗi request Jira: {str(e)}, transaction_id={transaction_id}")
            return NodeStatusSyncReply(
                success=False,
                error_message=f"Lỗi request Jira: {str(e)}",
                data={"transaction_id": transaction_id}
            ).model_dump()

        except Exception as e:
            log.error(f"[NodeStatusSyncHandler] Lỗi không xác định: {str(e)}, transaction_id={transaction_id}")
            return NodeStatusSyncReply(
                success=False,
                error_message=f"Lỗi không xác định: {str(e)}",
                data={"transaction_id": transaction_id}
            ).model_dump()
