from datetime import datetime, timezone
from typing import Any, Dict

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraSprintState, JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.jira_sprint import JiraSprintDBCreateDTO, JiraSprintDBUpdateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraSprintWebhookDTO
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class SprintStartWebhookHandler(JiraWebhookHandler):
    """Handler for sprint start webhooks"""

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
        return webhook_event in [JiraWebhookEvent.SPRINT_STARTED, "jira:sprint_started"]

    async def handle(self, session: AsyncSession, webhook_data: JiraSprintWebhookDTO) -> Dict[str, Any]:
        """Handle the sprint start webhook"""
        sprint_id = webhook_data.sprint.id

        # Get latest sprint data from Jira API
        sprint_data = await self.jira_sprint_api_service.get_sprint_by_id_with_admin_auth(sprint_id)
        if not sprint_data:
            log.error(f"Failed to fetch sprint {sprint_id} from Jira API")
            return {"error": f"Failed to fetch sprint {sprint_id}"}

        # Check if sprint exists in database
        existing_sprint = await self.sprint_database_service.get_sprint_by_jira_sprint_id(session=session, jira_sprint_id=sprint_id)

        try:
            if not existing_sprint:
                # Cần project_key cho sprint mới
                project_key = await self.get_project_key_for_sprint(sprint_id)
                if not project_key:
                    log.error(f"Could not determine project key for sprint {sprint_id}")
                    return {"error": f"Could not determine project key for sprint {sprint_id}"}

                # Sprint doesn't exist, create it
                create_dto = JiraSprintDBCreateDTO(
                    jira_sprint_id=sprint_id,
                    name=sprint_data.name,
                    state=JiraSprintState.ACTIVE.value,  # Set as ACTIVE since it's a start event
                    start_date=sprint_data.start_date or datetime.now(timezone.utc),
                    end_date=sprint_data.end_date,
                    complete_date=None,
                    goal=sprint_data.goal,
                    board_id=sprint_data.board_id,  # Lưu board_id
                    project_key=project_key,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                created_sprint = await self.sprint_database_service.create_sprint(session=session, sprint_data=create_dto)
                if not created_sprint:
                    return {"error": f"Failed to create sprint {sprint_id}"}

                operation_type = OperationType.CREATE
            else:
                # Sprint exists, update it
                update_dto = JiraSprintDBUpdateDTO(
                    name=sprint_data.name,
                    state=JiraSprintState.ACTIVE.value,  # Ensure state is ACTIVE
                    start_date=sprint_data.start_date or datetime.now(timezone.utc),
                    end_date=sprint_data.end_date,
                    goal=sprint_data.goal,
                    updated_at=datetime.now(timezone.utc),
                    board_id=sprint_data.board_id
                )
                updated_sprint = await self.sprint_database_service.update_sprint_by_jira_sprint_id(session=session, jira_sprint_id=sprint_id, sprint_data=update_dto)
                if not updated_sprint:
                    return {"error": f"Failed to update sprint {sprint_id}"}

                operation_type = OperationType.UPDATE

            # Log sync event
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.SPRINT.value,
                    entity_id=str(sprint_id),
                    operation=operation_type,
                    request_payload=webhook_data.model_dump(),
                    response_status=200,
                    response_body={"state": JiraSprintState.ACTIVE.value},
                    source=SourceType.WEBHOOK,
                    sender=None
                )
            )

            return {
                "sprint_id": sprint_id,
                "started": True,
                "operation": "created" if operation_type == OperationType.CREATE else "updated"
            }

        except Exception as e:
            log.error(f"Error processing sprint start webhook for sprint {sprint_id}: {str(e)}")
            return {"error": f"Failed to process sprint {sprint_id}: {str(e)}"}
