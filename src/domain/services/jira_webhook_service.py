from abc import ABC, abstractmethod
from typing import Any, Dict


class IJiraWebhookService(ABC):
    """Interface for Jira webhook service"""

    @abstractmethod
    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """Handle incoming webhook event"""
        pass
