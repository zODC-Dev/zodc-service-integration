from datetime import datetime, timezone
from typing import Any, Dict

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.jira_sprint import JiraSprintDBCreateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraSprintWebhookDTO
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class SprintCreateWebhookHandler(JiraWebhookHandler):
    """Handler for sprint creation webhooks"""

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
        return webhook_event in [JiraWebhookEvent.SPRINT_CREATED, "jira:sprint_created"]

    async def handle(self, webhook_data: JiraSprintWebhookDTO) -> Dict[str, Any]:
        """Handle the sprint creation webhook"""
        sprint_id = webhook_data.sprint.id

        # Get latest sprint data from Jira API
        sprint_data = await self.jira_sprint_api_service.get_sprint_by_id_with_system_user(sprint_id)
        if not sprint_data:
            log.error(f"Failed to fetch sprint {sprint_id} from Jira API")
            return {"error": f"Failed to fetch sprint {sprint_id}"}

        # Get project key
        project_key = await self.get_project_key_for_sprint(sprint_id)
        if not project_key:
            log.error(f"Could not determine project key for sprint {sprint_id}")
            return {"error": f"Could not determine project key for sprint {sprint_id}"}

        # Check if sprint already exists
        existing_sprint = await self.sprint_database_service.get_sprint_by_jira_sprint_id(sprint_id)
        if existing_sprint:
            return {"success": True, "message": f"Sprint {sprint_id} already exists"}

        try:
            # Create sprint using data from Jira API
            create_dto = JiraSprintDBCreateDTO(
                jira_sprint_id=sprint_id,
                name=sprint_data.name,
                state=sprint_data.state,
                start_date=sprint_data.start_date,
                end_date=sprint_data.end_date,
                complete_date=sprint_data.complete_date,
                goal=sprint_data.goal,
                board_id=sprint_data.board_id,
                project_key=project_key,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

            # Create sprint in database
            created_sprint = await self.sprint_database_service.create_sprint(create_dto)
            if not created_sprint:
                return {"error": f"Failed to create sprint {sprint_id}"}

            # Log sync event
            await self.sync_log_repository.create_sync_log(
                SyncLogDBCreateDTO(
                    entity_type=EntityType.SPRINT,
                    entity_id=str(sprint_id),
                    operation=OperationType.CREATE,
                    request_payload=webhook_data.model_dump(),
                    response_status=200,
                    response_body={},
                    source=SourceType.WEBHOOK,
                    sender=None
                )
            )

            return {
                "sprint_id": sprint_id,
                "created": True
            }

        except Exception as e:
            log.error(f"Error creating sprint {sprint_id}: {str(e)}")
            return {"error": f"Failed to create sprint {sprint_id}: {str(e)}"}
