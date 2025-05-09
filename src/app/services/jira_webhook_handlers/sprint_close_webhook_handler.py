from datetime import datetime, timezone
from typing import Any, Dict

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraSprintState, JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.jira_sprint import JiraSprintDBUpdateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraSprintWebhookDTO
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class SprintCloseWebhookHandler(JiraWebhookHandler):
    """Handler for sprint close webhooks"""

    def __init__(
        self,
        sprint_database_service: IJiraSprintDatabaseService,
        sync_log_repository: ISyncLogRepository,
        jira_sprint_api_service: IJiraSprintAPIService,
        jira_issue_repository: IJiraIssueRepository
    ):
        self.sprint_database_service = sprint_database_service
        self.sync_log_repository = sync_log_repository
        self.jira_sprint_api_service = jira_sprint_api_service
        self.jira_issue_repository = jira_issue_repository

    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        return webhook_event in [JiraWebhookEvent.SPRINT_CLOSED, "jira:sprint_closed", "sprint_closed"]

    async def handle(self, session: AsyncSession, webhook_data: JiraSprintWebhookDTO) -> Dict[str, Any]:
        """Handle the sprint close webhook"""
        sprint_id = webhook_data.sprint.id
        log.info(f"Processing sprint close webhook for sprint {sprint_id}")

        # Get latest sprint data from Jira API
        sprint_data = await self.jira_sprint_api_service.get_sprint_by_id_with_admin_auth(sprint_id)
        if not sprint_data:
            log.error(f"Failed to fetch sprint {sprint_id} from Jira API")
            return {"error": f"Failed to fetch sprint {sprint_id}"}

        # Update sprint in database with latest data
        update_dto = JiraSprintDBUpdateDTO(
            name=sprint_data.name,
            state=JiraSprintState.CLOSED.value,  # Ensure state is CLOSED
            start_date=sprint_data.start_date,
            end_date=sprint_data.end_date,
            complete_date=sprint_data.complete_date or datetime.now(timezone.utc),
            goal=sprint_data.goal,
            updated_at=datetime.now(timezone.utc)
        )

        updated_sprint = await self.sprint_database_service.update_sprint_by_jira_sprint_id(session=session, jira_sprint_id=sprint_id, sprint_data=update_dto)
        if not updated_sprint:
            return {"error": f"Failed to update sprint {sprint_id}"}

        # Reset is_system_linked flag for all issues in this sprint
        assert updated_sprint.id is not None, "sprint id is not None"
        await self.reset_system_linked_flag(session=session, sprint_id=updated_sprint.id)

        # Log sync event
        await self.sync_log_repository.create_sync_log(
            session=session,
            sync_log=SyncLogDBCreateDTO(
                entity_type=EntityType.SPRINT,
                entity_id=str(sprint_id),
                operation=OperationType.UPDATE,
                request_payload=webhook_data.model_dump(),
                response_status=200,
                response_body={"state": JiraSprintState.CLOSED.value},
                source=SourceType.WEBHOOK,
                sender=None
            )
        )

        return {
            "sprint_id": sprint_id,
            "closed": True
        }

    async def reset_system_linked_flag(self, session: AsyncSession, sprint_id: int) -> None:
        """Reset is_system_linked flag for all issues in a sprint"""
        try:
            # Since sprint_id here is Jira's sprint ID, we need to use our database ID
            db_sprint_id = sprint_id
            if db_sprint_id:
                updated_count = await self.jira_issue_repository.reset_system_linked_for_sprint(session=session, sprint_id=db_sprint_id)
                log.info(
                    f"Reset is_system_linked flag for {updated_count} issues in sprint {sprint_id} (DB ID: {db_sprint_id})")
            else:
                log.warning(f"Could not reset is_system_linked flag for issues: no DB ID found for sprint {sprint_id}")
        except Exception as e:
            log.error(f"Error resetting is_system_linked flag for issues in sprint {sprint_id}: {str(e)}")
            # We don't want to fail the webhook handling if resetting flags fails
            # So just log the error and continue
