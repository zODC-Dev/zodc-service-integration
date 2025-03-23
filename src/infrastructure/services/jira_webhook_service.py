from typing import Any, Dict

from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.models.jira_webhook import JiraWebhookPayload
from src.domain.services.jira_webhook_service import IJiraWebhookService


class JiraWebhookService(IJiraWebhookService):
    """Implementation of Jira webhook service"""

    def __init__(
        self,
        jira_issue_service: JiraIssueApplicationService
    ):
        self.jira_issue_service = jira_issue_service

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """Route webhook to appropriate handler"""
        try:
            # Parse webhook payload
            webhook_data = JiraWebhookPayload.parse_webhook(payload)

            if webhook_data.webhook_event == JiraWebhookEvent.ISSUE_CREATED:
                await self.jira_issue_service.handle_webhook_create(webhook_data)
            elif webhook_data.webhook_event == JiraWebhookEvent.ISSUE_UPDATED:
                await self.jira_issue_service.handle_webhook_update(webhook_data)
            else:
                log.warning(f"Unhandled webhook event type: {webhook_data.webhook_event}")

        except ValueError as e:
            log.error(f"Invalid webhook payload: {str(e)}")
            raise
        except Exception as e:
            log.error(f"Error processing webhook: {str(e)}")
            raise
