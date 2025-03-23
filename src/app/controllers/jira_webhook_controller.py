from typing import Any, Dict

from fastapi import HTTPException

from src.configs.logger import log
from src.domain.models.jira_webhook import JiraWebhookPayload
from src.domain.services.jira_webhook_service import IJiraWebhookService


class JiraWebhookController:
    def __init__(self, jira_webhook_service: IJiraWebhookService):
        self.jira_webhook_service = jira_webhook_service

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Handle incoming Jira webhook"""
        try:
            webhook_data = JiraWebhookPayload.parse_webhook(payload)
            result = await self.jira_webhook_service.handle_webhook(webhook_data)

            if result and "error" in result:
                raise HTTPException(status_code=400, detail=result["error"])

            return {"status": "success"}
        except Exception as e:
            log.error(f"Error in webhook handler: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e
