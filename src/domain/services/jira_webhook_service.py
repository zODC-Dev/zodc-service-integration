from abc import ABC, abstractmethod
from typing import Any, Dict

from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO


class IJiraWebhookService(ABC):
    """Interface for Jira webhook service"""

    @abstractmethod
    async def handle_webhook(self, webhook_data: JiraWebhookResponseDTO) -> Dict[str, Any]:
        """Handle incoming webhook event"""
        pass
