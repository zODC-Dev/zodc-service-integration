from typing import AsyncGenerator

from fastapi import Depends

from src.app.controllers.jira_webhook_controller import JiraWebhookController
from src.app.dependencies.base import get_issue_repository, get_sync_log_repository
from src.app.dependencies.jira_issue import get_jira_issue_api_service
from src.app.services.jira_webhook_queue_service import JiraWebhookQueueService
from src.infrastructure.services.jira_webhook_service import JiraWebhookService


async def get_webhook_service(
    jira_issue_repository=Depends(get_issue_repository),
    sync_log_repository=Depends(get_sync_log_repository),
    jira_issue_api_service=Depends(get_jira_issue_api_service)
) -> AsyncGenerator[JiraWebhookService, None]:
    """Get Jira webhook service"""
    yield JiraWebhookService(jira_issue_repository, sync_log_repository, jira_issue_api_service)


async def get_webhook_queue_service(
    jira_issue_api_service=Depends(get_jira_issue_api_service)
) -> AsyncGenerator[JiraWebhookQueueService, None]:
    """Get Jira webhook queue service"""
    yield JiraWebhookQueueService(jira_issue_api_service)


async def get_webhook_controller(
    webhook_service=Depends(get_webhook_service),
    webhook_queue_service=Depends(get_webhook_queue_service)
) -> AsyncGenerator[JiraWebhookController, None]:
    """Get Jira webhook controller"""
    yield JiraWebhookController(webhook_service, webhook_queue_service)
