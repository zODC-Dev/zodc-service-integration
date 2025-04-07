from typing import Any, Dict

from src.app.services.jira_issue_history_sync_service import JiraIssueHistorySyncService
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.jira_issue import JiraIssueDBUpdateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO
from src.domain.models.jira.webhooks.mappers.jira_issue_converter import JiraIssueConverter
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService


class IssueUpdateWebhookHandler(JiraWebhookHandler):
    """Handler for issue update webhooks"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository,
        jira_issue_api_service: IJiraIssueAPIService,
        issue_history_sync_service: JiraIssueHistorySyncService
    ):
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository
        self.jira_issue_api_service = jira_issue_api_service
        self.issue_history_sync_service = issue_history_sync_service

    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        return webhook_event == JiraWebhookEvent.ISSUE_UPDATED

    async def handle(self, webhook_data: JiraWebhookResponseDTO) -> Dict[str, Any]:
        """Handle the issue update webhook"""
        issue_id = webhook_data.issue.id

        # Log the webhook sync
        await self.sync_log_repository.create_sync_log(
            SyncLogDBCreateDTO(
                entity_type=EntityType.ISSUE,
                entity_id=issue_id,
                operation=OperationType.SYNC,
                request_payload=webhook_data.to_json_serializable(),
                response_status=200,
                response_body={},
                source=SourceType.WEBHOOK,
                sender=None
            )
        )

        # Lấy issue hiện tại từ database để so sánh thay đổi
        # current_issue = await self.jira_issue_repository.get_by_jira_issue_id(issue_id)

        # Get latest issue data from Jira API using system user
        issue_data = await self.jira_issue_api_service.get_issue_with_admin_auth(issue_id)
        if not issue_data:
            return {"error": "Failed to fetch issue data", "issue_id": issue_id}

        # Thay vì lưu history trực tiếp từ webhook, gọi service đồng bộ history từ API
        if self.issue_history_sync_service:
            try:
                await self.issue_history_sync_service.sync_issue_history(issue_id)
                log.info(f"Successfully synced history for issue {issue_id} from Jira API")
            except Exception as e:
                log.error(f"Error syncing history for issue {issue_id}: {str(e)}")

        # Update in database
        update_dto = JiraIssueConverter._convert_to_update_dto(issue_data)
        updated_issue = await self.jira_issue_repository.update(issue_id, update_dto)

        return {
            "issue_id": issue_id,
            "updated": updated_issue is not None
        }

    async def _handle_conflict(self, issue_id: str, remote_updated_at, local_updated_at):
        """Handle conflict when both remote and local changes exist"""
        log.warning(
            f"Conflict detected for issue {issue_id}. "
            f"Remote updated_at: {remote_updated_at}, Local last_synced_at: {local_updated_at}"
        )
        # Implement your conflict resolution strategy here

    async def _update_sync_status(self, issue_id: str, updated_at):
        """Update the sync status of an issue"""
        await self.jira_issue_repository.update(
            issue_id,
            JiraIssueDBUpdateDTO(
                last_synced_at=updated_at,
                updated_locally=False
            )
        )
