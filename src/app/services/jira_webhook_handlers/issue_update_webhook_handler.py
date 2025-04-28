from typing import Any, Dict

from src.app.services.jira_issue_history_service import JiraIssueHistoryApplicationService
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.app.services.nats_application_service import NATSApplicationService
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO
from src.domain.models.jira.webhooks.mappers.jira_issue_converter import JiraIssueConverter
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.nats.publishes.jira_issue_update import JiraIssueUpdateDataPublishDTO, JiraIssueUpdatePublishDTO
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService


class IssueUpdateWebhookHandler(JiraWebhookHandler):
    """Handler for issue update webhooks"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository,
        jira_issue_api_service: IJiraIssueAPIService,
        issue_history_sync_service: JiraIssueHistoryApplicationService,
        jira_sprint_repository: IJiraSprintRepository,
        nats_application_service: NATSApplicationService
    ):
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository
        self.jira_issue_api_service = jira_issue_api_service
        self.issue_history_sync_service = issue_history_sync_service
        self.nats_application_service = nats_application_service
        self.jira_sprint_repository = jira_sprint_repository

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
        current_issue = await self.jira_issue_repository.get_by_jira_issue_id(issue_id)
        if not current_issue:
            return {"error": "Issue not found", "issue_id": issue_id}

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

        # Publish issue update to NATS for masterflow service
        if updated_issue:
            try:
                await self._publish_issue_update_event(issue_data, current_issue)
                log.info(f"Published issue update event for issue {issue_id} to NATS")
            except Exception as e:
                log.error(f"Error publishing issue update event for issue {issue_id}: {str(e)}")

        return {
            "issue_id": issue_id,
            "updated": updated_issue is not None
        }

    async def _publish_issue_update_event(self, issue_data: JiraIssueModel, old_issue: JiraIssueModel) -> None:
        """Publish issue update event to NATS for masterflow service"""
        # Extract required data from issue_data
        jira_key = issue_data.key
        summary = issue_data.summary
        description = issue_data.description

        # Extract assignee email if available
        assignee = issue_data.assignee
        assignee_email = assignee.email if assignee else None
        assignee_id = assignee.user_id if assignee else None

        # Extract story points / estimate if available
        estimate_point = issue_data.estimate_point

        # Extract status
        status = issue_data.status.value

        # Extract sprint id by getting active sprint id
        sprint_id = None
        if issue_data.sprints:
            for sprint in issue_data.sprints:
                if sprint.state == "active":
                    jira_sprint_id = sprint.jira_sprint_id
                    current_sprint = await self.jira_sprint_repository.get_sprint_by_jira_sprint_id(jira_sprint_id)
                    if current_sprint:
                        sprint_id = current_sprint.id
                        break

        # Get updated timestamp
        updated_at = issue_data.updated_at

        # Get old status as string
        old_status = old_issue.status.value if old_issue.status else None

        # Create update data model
        update_data = JiraIssueUpdateDataPublishDTO(
            jira_key=jira_key,
            summary=summary,
            description=description,
            assignee_mail=assignee_email,
            assignee_id=assignee_id,
            estimate_point=estimate_point,
            status=status,
            sprint_id=sprint_id,
            updated_at=updated_at,
            old_status=old_status
        )

        # Create publish DTO and send via NATS
        publish_dto = JiraIssueUpdatePublishDTO.create(update_data)
        await self.nats_application_service.publish_event(publish_dto)
