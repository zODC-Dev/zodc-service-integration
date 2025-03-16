from typing import Any, Dict

from fastapi import HTTPException

from src.configs.logger import log
from src.domain.services.jira_webhook_service import IJiraWebhookService


class JiraWebhookController:
    def __init__(self, jira_webhook_service: IJiraWebhookService):
        self.jira_webhook_service = jira_webhook_service

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Handle incoming Jira webhook"""
        try:
            await self.jira_webhook_service.handle_webhook(payload)
            return {"status": "success"}
        except Exception as e:
            log.error(f"Error in webhook handler: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e
