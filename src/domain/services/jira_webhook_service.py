from abc import ABC, abstractmethod
from typing import Any, Dict

from src.domain.models.jira_webhook import JiraWebhookPayload


class IJiraWebhookService(ABC):
    """Interface for Jira webhook service"""

    @abstractmethod
    async def handle_webhook(self, webhook_data: JiraWebhookPayload) -> Dict[str, Any]:
        """Handle incoming webhook event"""
        pass
