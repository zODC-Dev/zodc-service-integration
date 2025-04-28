from typing import Any, Dict

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO
from src.domain.models.jira.webhooks.mappers.jira_issue_converter import JiraIssueConverter
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.redis_service import IRedisService


class IssueCreateWebhookHandler(JiraWebhookHandler):
    """Handler for issue creation webhooks"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository,
        jira_issue_api_service: IJiraIssueAPIService,
        jira_project_repository: IJiraProjectRepository,
        redis_service: IRedisService
    ):
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository
        self.jira_issue_api_service = jira_issue_api_service
        self.jira_project_repository = jira_project_repository
        self.redis_service = redis_service

    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        return webhook_event == JiraWebhookEvent.ISSUE_CREATED

    async def handle(self, webhook_data: JiraWebhookResponseDTO) -> Dict[str, Any]:
        """Handle the issue creation webhook"""
        issue_id = webhook_data.issue.id

        # Get latest issue data from Jira API
        issue_data = await self.get_latest_issue_data(issue_id)
        if not issue_data:
            return {"error": "Failed to fetch issue data", "issue_id": issue_id}

        # Create in database
        create_dto = JiraIssueConverter._convert_to_create_dto(issue_data)

        # Check if issue is system linked
        is_system_linked = await self.redis_service.get(f"system_linked:jira_issue:{issue_data.key}")
        if is_system_linked:
            create_dto.is_system_linked = True

        # Check if project key is exists in database
        project = await self.jira_project_repository.get_project_by_key(create_dto.project_key)
        if not project:
            log.warning(f"Project not found, project_key: {create_dto.project_key}")
            return {"error": "Project not found", "project_key": create_dto.project_key}

        await self.jira_issue_repository.create(create_dto)

        # Log sync
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

        log.info(f"Successfully created issue {issue_id} from webhook")

        return {
            "issue_id": issue_id,
            "created": True
        }
