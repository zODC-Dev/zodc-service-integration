from typing import Any, Dict, List, Optional

from src.app.services.jira_issue_history_sync_service import JiraIssueHistorySyncService
from src.app.services.jira_webhook_handlers.issue_create_webhook_handler import IssueCreateWebhookHandler
from src.app.services.jira_webhook_handlers.issue_delete_webhook_handler import IssueDeleteWebhookHandler
from src.app.services.jira_webhook_handlers.issue_update_webhook_handler import IssueUpdateWebhookHandler
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_close_webhook_handler import SprintCloseWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_create_webhook_handler import SprintCreateWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_delete_webhook_handler import SprintDeleteWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_start_webhook_handler import SprintStartWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_update_webhook_handler import SprintUpdateWebhookHandler
from src.configs.logger import log
from src.domain.models.jira.webhooks.jira_webhook import (
    BaseJiraWebhookDTO,
    JiraIssueWebhookDTO,
    JiraSprintWebhookDTO,
)
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class JiraWebhookService:
    """Service for handling Jira webhooks"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository,
        jira_issue_api_service: IJiraIssueAPIService,
        jira_sprint_api_service: IJiraSprintAPIService,
        sprint_database_service: IJiraSprintDatabaseService,
        issue_history_sync_service: JiraIssueHistorySyncService,
        jira_project_repository: IJiraProjectRepository
    ):
        self.handlers: List[JiraWebhookHandler] = []
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository
        self.jira_issue_api_service = jira_issue_api_service
        self.jira_sprint_api_service = jira_sprint_api_service
        self.sprint_database_service = sprint_database_service
        self.issue_history_sync_service = issue_history_sync_service
        self.jira_project_repository = jira_project_repository
        self._init_handlers()

    def _init_handlers(self) -> None:
        """Initialize webhook handlers"""
        # Issue handlers
        issue_handlers = [
            IssueCreateWebhookHandler(self.jira_issue_repository, self.sync_log_repository,
                                      self.jira_issue_api_service, self.jira_project_repository),
            IssueUpdateWebhookHandler(self.jira_issue_repository, self.sync_log_repository,
                                      self.jira_issue_api_service, self.issue_history_sync_service),
            IssueDeleteWebhookHandler(self.jira_issue_repository, self.sync_log_repository)
        ]

        # Sprint handlers - only add if sprint_database_service is provided
        sprint_handlers = []
        if self.sprint_database_service:
            sprint_handlers = [
                SprintCreateWebhookHandler(self.sprint_database_service, self.sync_log_repository,
                                           self.jira_sprint_api_service),
                SprintUpdateWebhookHandler(self.sprint_database_service, self.sync_log_repository,
                                           self.jira_sprint_api_service),
                SprintStartWebhookHandler(self.sprint_database_service, self.sync_log_repository,
                                          self.jira_sprint_api_service),
                SprintCloseWebhookHandler(self.sprint_database_service, self.sync_log_repository,
                                          self.jira_sprint_api_service),
                SprintDeleteWebhookHandler(self.sprint_database_service, self.sync_log_repository,
                                           self.jira_sprint_api_service)
            ]

        # Combine all handlers
        self.handlers = issue_handlers + sprint_handlers

    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a webhook by delegating to appropriate handler"""
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

            # Process with handlers
            for handler in self.handlers:
                result = await handler.process(parsed_webhook)
                if result is not None:
                    return result

            log.warning(f"No handler found for webhook event: {parsed_webhook.webhook_event}")
            return {"error": f"Unsupported webhook event: {parsed_webhook.webhook_event}"}

        except Exception as e:
            log.error(f"Error handling webhook: {str(e)}")
            return {"error": str(e)}
