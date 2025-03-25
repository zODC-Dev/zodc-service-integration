from typing import Any, Dict, List, Optional

from src.app.services.jira_webhook_handlers.issue_create_webhook_handler import IssueCreateWebhookHandler
from src.app.services.jira_webhook_handlers.issue_delete_webhook_handler import IssueDeleteWebhookHandler
from src.app.services.jira_webhook_handlers.issue_update_webhook_handler import IssueUpdateWebhookHandler
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService


class JiraWebhookService:
    """Service for handling Jira webhooks"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository,
        jira_issue_api_service: IJiraIssueAPIService
    ):
        self.handlers: List[JiraWebhookHandler] = []
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository
        self.jira_issue_api_service = jira_issue_api_service
        self._init_handlers()

    def _init_handlers(self):
        """Initialize webhook handlers"""
        self.handlers = [
            IssueCreateWebhookHandler(self.jira_issue_repository, self.sync_log_repository,
                                      self.jira_issue_api_service),
            IssueUpdateWebhookHandler(self.jira_issue_repository, self.sync_log_repository,
                                      self.jira_issue_api_service),
            IssueDeleteWebhookHandler(self.jira_issue_repository, self.sync_log_repository)
            # Add more handlers as needed
        ]

    async def handle_webhook(self, webhook_data: JiraWebhookResponseDTO) -> Optional[Dict[str, Any]]:
        """Handle a webhook by delegating to appropriate handler"""
        try:
            log.info(f"Received webhook event: {webhook_data.webhook_event}")

            # Validate webhook data
            if not webhook_data.webhook_event:
                log.error("Webhook event type is missing")
                return {"error": "Missing webhook event type"}

            if not webhook_data.issue or not webhook_data.issue.id:
                log.error("Webhook is missing issue data")
                return {"error": "Missing issue data"}

            # Try all handlers
            for handler in self.handlers:
                result = await handler.process(webhook_data)
                if result is not None:
                    return result

            log.warning(f"No handler found for webhook event: {webhook_data.webhook_event}")
            return {"error": f"Unsupported webhook event: {webhook_data.webhook_event}"}

        except Exception as e:
            log.error(f"Error handling webhook: {str(e)}")
            return {"error": str(e)}
