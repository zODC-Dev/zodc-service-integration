from typing import AsyncGenerator

from fastapi import Depends

from src.app.controllers.jira_issue_controller import JiraIssueController
from src.app.dependencies.base import (
    get_issue_repository,
    get_nats_service,
    get_project_repository,
    get_sync_log_repository,
)
from src.app.dependencies.common import get_jira_api_admin_client, get_jira_api_client, get_jira_user_repository
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.infrastructure.services.jira_issue_api_service import JiraIssueAPIService
from src.infrastructure.services.jira_issue_database_service import JiraIssueDatabaseService


async def get_jira_issue_api_service(
    jira_api_client=Depends(get_jira_api_client),
    jira_api_admin_client=Depends(get_jira_api_admin_client),
    user_repository=Depends(get_jira_user_repository)
) -> AsyncGenerator[JiraIssueAPIService, None]:
    """Get Jira issue API service"""
    yield JiraIssueAPIService(
        client=jira_api_client,
        user_repository=user_repository,
        admin_client=jira_api_admin_client
    )


async def get_jira_issue_database_service(
    issue_repository=Depends(get_issue_repository)
) -> AsyncGenerator[JiraIssueDatabaseService, None]:
    """Get Jira issue database service"""
    yield JiraIssueDatabaseService(issue_repository=issue_repository)


async def get_jira_issue_service(
    issue_api_service=Depends(get_jira_issue_api_service),
    issue_db_service=Depends(get_jira_issue_database_service),
    issue_repository=Depends(get_issue_repository),
    project_repository=Depends(get_project_repository),
    nats_service=Depends(get_nats_service),
    sync_log_repository=Depends(get_sync_log_repository),
) -> AsyncGenerator[JiraIssueApplicationService, None]:
    """Get Jira issue application service"""
    yield JiraIssueApplicationService(
        jira_issue_db_service=issue_db_service,
        jira_issue_api_service=issue_api_service,
        issue_repository=issue_repository,
        project_repository=project_repository,
        nats_service=nats_service,
        sync_log_repository=sync_log_repository
    )


async def get_jira_issue_controller(
    issue_service=Depends(get_jira_issue_service),
) -> AsyncGenerator[JiraIssueController, None]:
    """Get Jira issue controller"""
    yield JiraIssueController(jira_issue_service=issue_service)
