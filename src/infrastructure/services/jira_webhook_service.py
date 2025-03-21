from typing import Any, Dict

from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.domain.services.jira_webhook_service import IJiraWebhookService


class JiraWebhookService(IJiraWebhookService):
    """Implementation of Jira webhook service"""

    def __init__(
        self,
        jira_issue_service: JiraIssueApplicationService
    ):
        self.jira_issue_service = jira_issue_service

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """Delegate to JiraIssueDatabaseService"""
        await self.jira_issue_service.handle_webhook_update(payload)
