from typing import Any, Dict

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.jira_webhook import JiraWebhookPayload
from src.domain.models.sync_log import SyncLogCreateDTO
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.infrastructure.mappers.jira_webhook_mapper import JiraWebhookMapper


class IssueCreateWebhookHandler(JiraWebhookHandler):
    """Handler for issue creation webhooks"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository
    ):
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository

    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        return webhook_event == JiraWebhookEvent.ISSUE_CREATED

    async def handle(self, webhook_data: JiraWebhookPayload) -> Dict[str, Any]:
        """Handle the issue creation webhook"""
        issue_id = webhook_data.issue.id

        # Log the webhook sync first
        await self.sync_log_repository.create_sync_log(
            SyncLogCreateDTO(
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

        # Map webhook data to DTO
        issue_create_dto = JiraWebhookMapper.map_to_create_dto(webhook_data)

        # Save to database with transaction
        await self.jira_issue_repository.create(issue_create_dto)

        log.info(f"Successfully created issue {issue_id} from webhook")

        return {
            "issue_id": issue_id,
            "created": True
        }
