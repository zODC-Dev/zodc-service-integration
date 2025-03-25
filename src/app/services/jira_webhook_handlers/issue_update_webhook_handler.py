from datetime import datetime
from typing import Any, Dict

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.jira_issue import JiraIssueDBUpdateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO
from src.domain.models.jira.webhooks.mappers.jira_webhook import JiraWebhookMapper
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository


class IssueUpdateWebhookHandler(JiraWebhookHandler):
    """Handler for issue update webhooks"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository
    ):
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository

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

        # Get existing issue
        issue = await self.jira_issue_repository.get_by_jira_issue_id(issue_id)
        if not issue:
            log.warning(f"Issue {issue_id} not found in database")
            return {"error": "Issue not found", "issue_id": issue_id}

        # Map webhook data to update dict
        update_data = JiraWebhookMapper.map_to_update_dto(webhook_data)

        # Check for conflicts
        updated_at: datetime = update_data.get("updated_at")
        if issue.updated_locally and updated_at > issue.last_synced_at:
            await self._handle_conflict(issue_id, updated_at, issue.last_synced_at)

        # Update if there are changes
        updated_issue = None
        if update_data:
            updated_issue = await self.jira_issue_repository.update(
                issue_id,
                JiraIssueDBUpdateDTO(**update_data)
            )

        # Update sync status
        await self._update_sync_status(issue_id, update_data["updated_at"])

        log.info(f"Successfully processed issue update webhook for issue {issue_id}")

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
