from datetime import datetime, timezone
from typing import Any, Dict

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.jira_user import JiraUserDBUpdateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraUserWebhookDTO
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_user_database_service import IJiraUserDatabaseService


class UserDeleteWebhookHandler(JiraWebhookHandler):
    """Handler for user delete webhooks"""

    def __init__(
        self,
        user_database_service: IJiraUserDatabaseService,
        sync_log_repository: ISyncLogRepository
    ):
        self.sync_log_repository = sync_log_repository
        self.user_database_service = user_database_service

    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        return webhook_event in [JiraWebhookEvent.USER_DELETED, "jira:user_deleted"]

    async def handle(self, webhook_data: JiraUserWebhookDTO) -> Dict[str, Any]:
        """Handle the user delete webhook"""
        account_id = webhook_data.user.account_id
        log.info(f"Processing user delete webhook for user {account_id}")

        try:
            # Check if user exists
            existing_user = await self.user_database_service.get_user_by_jira_account_id(account_id)

            if not existing_user:
                log.warning(f"User {account_id} not found in database, nothing to delete")
                return {"warning": f"User {account_id} not found in database"}

            # Update user to inactive instead of deleting
            update_dto = JiraUserDBUpdateDTO(
                is_active=False,
                updated_at=datetime.now(timezone.utc)
            )

            updated_user = await self.user_database_service.update_user_by_jira_account_id(account_id, update_dto)
            success = updated_user is not None

            # Log sync event
            await self.sync_log_repository.create_sync_log(
                SyncLogDBCreateDTO(
                    entity_type=EntityType.USER,
                    entity_id=account_id,
                    operation=OperationType.DELETE,
                    request_payload=webhook_data.model_dump(),
                    response_status=200 if success else 500,
                    response_body={"is_active": False},
                    source=SourceType.WEBHOOK,
                    sender=None
                )
            )

            if not success:
                return {"error": f"Failed to deactivate user {account_id}"}

            log.info(f"Successfully marked user {account_id} as inactive")
            return {
                "account_id": account_id,
                "deactivated": True
            }

        except Exception as e:
            log.error(f"Error handling user delete webhook: {str(e)}")
            return {"error": f"Error processing user deletion {account_id}: {str(e)}"}
