from typing import List

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.dependencies.base import get_sync_log_repository
from src.app.dependencies.common import get_jira_api_client
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_close_webhook_handler import SprintCloseWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_create_webhook_handler import SprintCreateWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_start_webhook_handler import SprintStartWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_update_webhook_handler import SprintUpdateWebhookHandler
from src.configs.database import get_db
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService
from src.infrastructure.repositories.sqlalchemy_jira_sprint_repository import SQLAlchemyJiraSprintRepository
from src.infrastructure.services.jira_service import JiraAPIClient
from src.infrastructure.services.jira_sprint_api_service import JiraSprintAPIService
from src.infrastructure.services.jira_sprint_database_service import JiraSprintDatabaseService


async def get_jira_sprint_api_service(
    jira_api_client: JiraAPIClient = Depends(get_jira_api_client),
) -> IJiraSprintAPIService:
    """Get the Jira sprint API service"""
    return JiraSprintAPIService(jira_api_client)


async def get_jira_sprint_repository(
    session: AsyncSession = Depends(get_db)
) -> IJiraSprintRepository:
    """Get the Jira sprint repository"""
    return SQLAlchemyJiraSprintRepository(session)


async def get_jira_sprint_database_service(
    sprint_repository: IJiraSprintRepository = Depends(get_jira_sprint_repository)
) -> IJiraSprintDatabaseService:
    """Get the Jira sprint database service"""
    return JiraSprintDatabaseService(sprint_repository)


async def get_sprint_create_webhook_handler(
    sprint_database_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service),
    sync_log_repository: ISyncLogRepository = Depends(get_sync_log_repository),
    jira_sprint_api_service: IJiraSprintAPIService = Depends(get_jira_sprint_api_service)
) -> JiraWebhookHandler:
    """Get the sprint create webhook handler"""
    return SprintCreateWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service)


async def get_sprint_update_webhook_handler(
    sprint_database_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service),
    sync_log_repository: ISyncLogRepository = Depends(get_sync_log_repository),
    jira_sprint_api_service: IJiraSprintAPIService = Depends(get_jira_sprint_api_service)
) -> JiraWebhookHandler:
    """Get the sprint update webhook handler"""
    return SprintUpdateWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service)


async def get_sprint_start_webhook_handler(
    sprint_database_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service),
    sync_log_repository: ISyncLogRepository = Depends(get_sync_log_repository),
    jira_sprint_api_service: IJiraSprintAPIService = Depends(get_jira_sprint_api_service)
) -> JiraWebhookHandler:
    """Get the sprint start webhook handler"""
    return SprintStartWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service)


async def get_sprint_close_webhook_handler(
    sprint_database_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service),
    sync_log_repository: ISyncLogRepository = Depends(get_sync_log_repository),
    jira_sprint_api_service: IJiraSprintAPIService = Depends(get_jira_sprint_api_service)
) -> JiraWebhookHandler:
    """Get the sprint close webhook handler"""
    return SprintCloseWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service)


async def get_sprint_webhook_handlers(
    sprint_create_handler: JiraWebhookHandler = Depends(get_sprint_create_webhook_handler),
    sprint_update_handler: JiraWebhookHandler = Depends(get_sprint_update_webhook_handler),
    sprint_start_handler: JiraWebhookHandler = Depends(get_sprint_start_webhook_handler),
    sprint_close_handler: JiraWebhookHandler = Depends(get_sprint_close_webhook_handler)
) -> List[JiraWebhookHandler]:
    """Get all sprint webhook handlers"""
    return [
        sprint_create_handler,
        sprint_update_handler,
        sprint_start_handler,
        sprint_close_handler
    ]
