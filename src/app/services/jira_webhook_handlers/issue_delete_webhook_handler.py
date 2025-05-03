from datetime import datetime, timezone
from typing import Any, Dict

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.jira_issue import JiraIssueDBUpdateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository


class IssueDeleteWebhookHandler(JiraWebhookHandler):
    """Handler for issue delete webhooks"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository
    ):
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository

    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        return webhook_event == JiraWebhookEvent.ISSUE_DELETED

    async def handle(self, session: AsyncSession, webhook_data: JiraWebhookResponseDTO) -> Dict[str, Any]:
        """Handle the issue deletion webhook"""
        issue_id = webhook_data.issue.id

        # Log the webhook sync
        await self.sync_log_repository.create_sync_log(
            session=session,
            sync_log=SyncLogDBCreateDTO(
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
        issue = await self.jira_issue_repository.get_by_jira_issue_id(session=session, jira_issue_id=issue_id)
        if not issue:
            log.warning(f"Issue {issue_id} not found in database, can't mark as deleted")
            return {"error": "Issue not found", "issue_id": issue_id}

        # Mark as deleted instead of removing
        await self.jira_issue_repository.update(
            session=session,
            issue_id=issue_id,
            issue_update=JiraIssueDBUpdateDTO(
                is_deleted=True,
                updated_at=issue.updated_at,  # Preserve the last updated time
                last_synced_at=datetime.now(timezone.utc)
            )
        )

        log.info(f"Successfully marked issue {issue_id} as deleted")

        return {
            "issue_id": issue_id,
            "deleted": True
        }
