from typing import AsyncGenerator

from fastapi import Depends

from src.app.controllers.jira_webhook_controller import JiraWebhookController
from src.app.dependencies.jira_issue import get_jira_issue_application_service
from src.infrastructure.services.jira_webhook_service import JiraWebhookService


async def get_webhook_service(
    issue_service=Depends(get_jira_issue_application_service)
) -> AsyncGenerator[JiraWebhookService, None]:
    """Get Jira webhook service"""
    yield JiraWebhookService(issue_service)


async def get_webhook_controller(
    webhook_service=Depends(get_webhook_service)
) -> AsyncGenerator[JiraWebhookController, None]:
    """Get Jira webhook controller"""
    yield JiraWebhookController(webhook_service)
