from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.configs.logger import log
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO


class JiraWebhookHandler(ABC):
    """Base class for all webhook handlers"""

    @abstractmethod
    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        pass

    @abstractmethod
    async def handle(self, webhook_data: JiraWebhookResponseDTO) -> Dict[str, Any]:
        """Handle the webhook event and return the result"""
        pass

    async def process(self, webhook_data: JiraWebhookResponseDTO) -> Optional[Dict[str, Any]]:
        """Process the webhook if this handler can handle it"""
        try:
            event_type = webhook_data.webhook_event

            if not await self.can_handle(event_type):
                return None

            log.info(f"Processing webhook event {event_type} with handler {self.__class__.__name__}")
            result = await self.handle(webhook_data)
            log.info(f"Successfully processed webhook event {event_type}")
            return result

        except Exception as e:
            log.error(f"Error processing webhook: {str(e)}")
            raise
