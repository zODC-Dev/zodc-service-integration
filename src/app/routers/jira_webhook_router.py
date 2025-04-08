from typing import Any, Dict

from fastapi import APIRouter, Depends

from src.app.controllers.jira_webhook_controller import JiraWebhookController
from src.app.dependencies.controllers import get_webhook_controller
from src.configs.logger import log

router = APIRouter()


@router.post("/webhook")
async def jira_webhook(
    payload: Dict[str, Any],
    controller: JiraWebhookController = Depends(get_webhook_controller)
) -> Dict[str, str]:
    """Handle Jira webhook events"""
    log.info(f"Received Jira webhook event: {payload}")
    return await controller.handle_webhook(payload)
