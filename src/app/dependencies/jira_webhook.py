from typing import AsyncGenerator, List

from fastapi import Depends

from src.app.controllers.jira_webhook_controller import JiraWebhookController
from src.app.dependencies.base import get_issue_repository, get_sync_log_repository
from src.app.dependencies.jira_issue import get_jira_issue_api_service
from src.app.dependencies.jira_issue_history import get_jira_issue_history_database_service
from src.app.dependencies.jira_sprint import get_jira_sprint_api_service, get_jira_sprint_database_service
from src.app.dependencies.jira_user import (
    get_jira_user_api_service,
    get_jira_user_database_service,
    get_user_repository,
)
from src.app.services.jira_issue_history_sync_service import JiraIssueHistorySyncService
from src.app.services.jira_webhook_handlers.issue_create_webhook_handler import IssueCreateWebhookHandler
from src.app.services.jira_webhook_handlers.issue_delete_webhook_handler import IssueDeleteWebhookHandler
from src.app.services.jira_webhook_handlers.issue_update_webhook_handler import IssueUpdateWebhookHandler
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_close_webhook_handler import SprintCloseWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_create_webhook_handler import SprintCreateWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_delete_webhook_handler import SprintDeleteWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_start_webhook_handler import SprintStartWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_update_webhook_handler import SprintUpdateWebhookHandler
from src.app.services.jira_webhook_handlers.user_create_webhook_handler import UserCreateWebhookHandler
from src.app.services.jira_webhook_handlers.user_delete_webhook_handler import UserDeleteWebhookHandler
from src.app.services.jira_webhook_handlers.user_update_webhook_handler import UserUpdateWebhookHandler
from src.app.services.jira_webhook_queue_service import JiraWebhookQueueService
from src.infrastructure.services.jira_webhook_service import JiraWebhookService


async def get_jira_issue_history_sync_service(
    jira_issue_api_service=Depends(get_jira_issue_api_service),
    jira_issue_history_database_service=Depends(get_jira_issue_history_database_service)
) -> JiraIssueHistorySyncService:
    """Get Jira issue history sync service"""
    return JiraIssueHistorySyncService(jira_issue_api_service, jira_issue_history_database_service)


async def get_webhook_handlers(
    jira_issue_repository=Depends(get_issue_repository),
    sync_log_repository=Depends(get_sync_log_repository),
    jira_issue_api_service=Depends(get_jira_issue_api_service),
    sprint_database_service=Depends(get_jira_sprint_database_service),
    jira_sprint_api_service=Depends(get_jira_sprint_api_service),
    jira_user_repository=Depends(get_user_repository),
    jira_user_api_service=Depends(get_jira_user_api_service),
    user_database_service=Depends(get_jira_user_database_service),
    issue_history_sync_service=Depends(get_jira_issue_history_sync_service)
) -> List[JiraWebhookHandler]:
    """Get list of webhook handlers with dependencies"""
    return [
        # Issue handlers
        IssueCreateWebhookHandler(jira_issue_repository, sync_log_repository, jira_issue_api_service),
        IssueUpdateWebhookHandler(jira_issue_repository, sync_log_repository,
                                  jira_issue_api_service, issue_history_sync_service),
        IssueDeleteWebhookHandler(jira_issue_repository, sync_log_repository),

        # Sprint handlers
        SprintCreateWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service),
        SprintUpdateWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service),
        SprintStartWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service),
        SprintCloseWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service),
        SprintDeleteWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service),

        # User handlers
        UserCreateWebhookHandler(user_database_service, sync_log_repository, jira_user_api_service),
        UserUpdateWebhookHandler(user_database_service, sync_log_repository, jira_user_api_service),
        UserDeleteWebhookHandler(user_database_service, sync_log_repository)
    ]


async def get_webhook_service(
    jira_issue_repository=Depends(get_issue_repository),
    sync_log_repository=Depends(get_sync_log_repository),
    jira_issue_api_service=Depends(get_jira_issue_api_service),
    jira_sprint_api_service=Depends(get_jira_sprint_api_service),
    sprint_database_service=Depends(get_jira_sprint_database_service),
    issue_history_sync_service=Depends(get_jira_issue_history_sync_service)
) -> AsyncGenerator[JiraWebhookService, None]:
    """Get Jira webhook service"""
    yield JiraWebhookService(jira_issue_repository, sync_log_repository, jira_issue_api_service, jira_sprint_api_service, sprint_database_service, issue_history_sync_service)


async def get_webhook_queue_service(
    jira_issue_api_service=Depends(get_jira_issue_api_service),
    jira_sprint_api_service=Depends(get_jira_sprint_api_service),
    jira_issue_history_service=Depends(get_jira_issue_history_database_service),
    webhook_handlers=Depends(get_webhook_handlers)
) -> AsyncGenerator[JiraWebhookQueueService, None]:
    """Get Jira webhook queue service"""
    yield JiraWebhookQueueService(jira_issue_api_service, jira_sprint_api_service, jira_issue_history_service, webhook_handlers)


async def get_webhook_controller(
    webhook_service=Depends(get_webhook_service),
    webhook_queue_service=Depends(get_webhook_queue_service)
) -> AsyncGenerator[JiraWebhookController, None]:
    """Get Jira webhook controller"""
    yield JiraWebhookController(webhook_service, webhook_queue_service)
