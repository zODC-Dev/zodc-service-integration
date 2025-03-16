from typing import Any, Dict

from src.configs.logger import log
from src.domain.entities.jira_webhook import JiraWebhookEvent
from src.domain.services.jira_webhook_service import IJiraWebhookService


class JiraWebhookService(IJiraWebhookService):
    """Implementation of Jira webhook service"""

    async def handle_webhook(self, payload: Dict[str, Any]) -> None:
        """Handle incoming webhook event"""
        try:
            # Convert payload to domain entity
            event = JiraWebhookEvent.from_webhook_payload(payload)

            # Log the event details
            log.info(f"Received Jira webhook event: {payload}")

            if event.changelog:
                log.info("Changes:")
                for item in event.changelog.get("items", []):
                    log.info(f"- Field '{item.get('field')}' changed from "
                             f"'{item.get('fromString')}' to '{item.get('toString')}'")

        except Exception as e:
            log.error(f"Error processing Jira webhook: {str(e)}")
            raise
