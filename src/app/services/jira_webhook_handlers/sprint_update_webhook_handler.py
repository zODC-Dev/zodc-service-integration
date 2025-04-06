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


class SprintUpdateWebhookHandler(JiraWebhookHandler):
    """Handler for sprint update webhooks"""

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
        return webhook_event in [JiraWebhookEvent.SPRINT_UPDATED, "jira:sprint_updated"]

    async def handle(self, webhook_data: JiraSprintWebhookDTO) -> Dict[str, Any]:
        """Handle the sprint update webhook"""
        sprint_id = webhook_data.sprint.id

        # Get latest sprint data from Jira API
        sprint_data = await self.jira_sprint_api_service.get_sprint_by_id_with_system_user(sprint_id)
        if not sprint_data:
            log.error(f"Failed to fetch sprint {sprint_id} from Jira API")
            return {"error": f"Failed to fetch sprint {sprint_id}"}

        # Update sprint in database with latest data
        update_dto = JiraSprintDBUpdateDTO(
            name=sprint_data.name,
            state=sprint_data.state,
            start_date=sprint_data.start_date,
            end_date=sprint_data.end_date,
            complete_date=sprint_data.complete_date,
            goal=sprint_data.goal,
            updated_at=datetime.now(timezone.utc),
            board_id=sprint_data.board_id
        )

        updated_sprint = await self.sprint_database_service.update_sprint_by_jira_sprint_id(sprint_id, update_dto)
        if not updated_sprint:
            return {"error": f"Failed to update sprint {sprint_id}"}

        # Log sync event
        await self.sync_log_repository.create_sync_log(
            SyncLogDBCreateDTO(
                entity_type=EntityType.SPRINT,
                entity_id=str(sprint_id),
                operation=OperationType.UPDATE,
                request_payload=webhook_data.model_dump(),
                response_status=200,
                response_body={},
                source=SourceType.WEBHOOK,
                sender=None
            )
        )

        return {
            "sprint_id": sprint_id,
            "updated": True
        }
