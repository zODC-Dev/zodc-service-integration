from datetime import datetime, timezone
from typing import Any, Dict

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.jira_sprint import JiraSprintDBUpdateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraSprintWebhookDTO
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class SprintDeleteWebhookHandler(JiraWebhookHandler):
    """Handler for sprint delete webhooks"""

    def __init__(
        self,
        sprint_database_service: IJiraSprintDatabaseService,
        sync_log_repository: ISyncLogRepository,
        jira_sprint_api_service: IJiraSprintAPIService
    ):
        self.sprint_database_service = sprint_database_service
        self.sync_log_repository = sync_log_repository
        self.jira_sprint_api_service = jira_sprint_api_service

    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        return webhook_event in [JiraWebhookEvent.SPRINT_DELETED, "jira:sprint_deleted"]

    async def handle(self, webhook_data: JiraSprintWebhookDTO) -> Dict[str, Any]:
        """Handle the sprint delete webhook"""
        sprint_id = webhook_data.sprint.id

        try:
            # Check if sprint exists
            existing_sprint = await self.sprint_database_service.get_sprint_by_jira_sprint_id(sprint_id)

            if not existing_sprint:
                log.warning(f"Sprint {sprint_id} not found in database, nothing to delete")
                return {"error": f"Sprint {sprint_id} not found"}

            # Update sprint as deleted
            update_dto = JiraSprintDBUpdateDTO(
                name=existing_sprint.name,
                state=existing_sprint.state,
                start_date=existing_sprint.start_date,
                end_date=existing_sprint.end_date,
                complete_date=existing_sprint.complete_date,
                goal=existing_sprint.goal,
                board_id=existing_sprint.board_id,
                is_deleted=True,
                updated_at=datetime.now(timezone.utc)
            )

            # Soft delete the sprint
            updated_sprint = await self.sprint_database_service.update_sprint_by_jira_sprint_id(
                sprint_id,
                update_dto
            )

            success = updated_sprint is not None

            # Log sync event
            await self.sync_log_repository.create_sync_log(
                SyncLogDBCreateDTO(
                    entity_type=EntityType.SPRINT,
                    entity_id=str(sprint_id),
                    operation=OperationType.DELETE,
                    request_payload=webhook_data.model_dump(),
                    response_status=200 if success else 500,
                    response_body={"is_deleted": True},
                    source=SourceType.WEBHOOK,
                    sender=None
                )
            )

            if not success:
                return {"error": f"Failed to delete sprint {sprint_id}"}

            return {
                "sprint_id": sprint_id,
                "deleted": True
            }

        except Exception as e:
            log.error(f"Error processing sprint delete webhook for sprint {sprint_id}: {str(e)}")
            return {"error": f"Failed to process sprint {sprint_id}: {str(e)}"}
