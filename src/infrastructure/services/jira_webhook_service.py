from typing import Any, Dict, List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_issue_history_service import JiraIssueHistoryApplicationService
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.app.services.nats_application_service import NATSApplicationService
from src.configs.logger import log
from src.domain.models.jira.webhooks.jira_webhook import (
    BaseJiraWebhookDTO,
    JiraIssueWebhookDTO,
    JiraSprintWebhookDTO,
)
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService
from src.domain.services.redis_service import IRedisService


class JiraWebhookService:
    """Service for handling Jira webhooks"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository,
        jira_issue_api_service: IJiraIssueAPIService,
        jira_sprint_api_service: IJiraSprintAPIService,
        sprint_database_service: IJiraSprintDatabaseService,
        issue_history_sync_service: JiraIssueHistoryApplicationService,
        jira_project_repository: IJiraProjectRepository,
        redis_service: IRedisService,
        jira_sprint_repository: IJiraSprintRepository,
        nats_application_service: NATSApplicationService = None,
        handlers: List[JiraWebhookHandler] = None
    ):
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository
        self.jira_issue_api_service = jira_issue_api_service
        self.jira_sprint_api_service = jira_sprint_api_service
        self.sprint_database_service = sprint_database_service
        self.issue_history_sync_service = issue_history_sync_service
        self.jira_project_repository = jira_project_repository
        self.redis_service = redis_service
        self.nats_application_service = nats_application_service
        self.jira_sprint_repository = jira_sprint_repository

        # Sử dụng handlers được cung cấp hoặc tạo mới
        self.handlers = handlers or []

    async def handle_webhook(self, session: AsyncSession, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a webhook by delegating to appropriate handler

        Args:
            session: The database session to use for database operations
            webhook_data: The webhook data to process

        Returns:
            The result of the handler or None if no handler was found
        """
        try:
            # Parse webhook using factory method
            parsed_webhook = BaseJiraWebhookDTO.parse_webhook(webhook_data)

            log.info(f"Received webhook event: {parsed_webhook.webhook_event}")

            # Validate basic webhook data
            if not parsed_webhook.webhook_event:
                log.error("Webhook event type is missing")
                return {"error": "Missing webhook event type"}

            # Kiểm tra type của webhook và validate phù hợp
            if isinstance(parsed_webhook, JiraIssueWebhookDTO):
                # Validate issue fields using attribute access instead of dict access
                if not hasattr(parsed_webhook, 'issue') or not parsed_webhook.issue or not parsed_webhook.issue.id:
                    log.error("Issue webhook is missing issue data")
                    return {"error": "Missing issue data"}

            elif isinstance(parsed_webhook, JiraSprintWebhookDTO):
                # Validate sprint fields using attribute access
                if not hasattr(parsed_webhook, 'sprint') or not parsed_webhook.sprint or not parsed_webhook.sprint.id:
                    log.error("Sprint webhook is missing sprint data")
                    return {"error": "Missing sprint data"}

            # Process with handlers, passing the session
            for handler in self.handlers:
                result = await handler.process(session, parsed_webhook)
                if result is not None:
                    return result

            log.warning(f"No handler found for webhook event: {parsed_webhook.webhook_event}")
            return {"error": f"Unsupported webhook event: {parsed_webhook.webhook_event}"}

        except Exception as e:
            log.error(f"Error handling webhook: {str(e)}")
            return {"error": str(e)}
