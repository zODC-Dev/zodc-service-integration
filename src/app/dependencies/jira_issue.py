from typing import AsyncGenerator

from fastapi import Depends

from src.app.controllers.jira_issue_controller import JiraIssueController
from src.app.dependencies.base import (
    get_issue_repository,
    get_nats_service,
    get_project_repository,
    get_sync_log_repository,
)
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.infrastructure.services.jira_issue_api_service import JiraIssueAPIService
from src.infrastructure.services.jira_issue_database_service import JiraIssueDatabaseService


async def get_jira_issue_api_service(
) -> AsyncGenerator[JiraIssueAPIService, None]:
    """Get Jira issue API service"""
    yield JiraIssueAPIService()


async def get_jira_issue_database_service(
    issue_repository=Depends(get_issue_repository)
) -> AsyncGenerator[JiraIssueDatabaseService, None]:
    """Get Jira issue database service"""
    yield JiraIssueDatabaseService(issue_repository)


async def get_jira_issue_application_service(
    issue_db_service=Depends(get_jira_issue_database_service),
    issue_api_service=Depends(get_jira_issue_api_service),
    issue_repository=Depends(get_issue_repository),
    project_repository=Depends(get_project_repository),
    nats_service=Depends(get_nats_service),
    sync_log_repository=Depends(get_sync_log_repository)
) -> AsyncGenerator[JiraIssueApplicationService, None]:
    """Get Jira issue application service"""
    yield JiraIssueApplicationService(
        issue_db_service,
        issue_api_service,
        issue_repository,
        project_repository,
        nats_service,
        sync_log_repository
    )


def get_jira_issue_controller(
    jira_issue_service: JiraIssueApplicationService = Depends(get_jira_issue_application_service)
) -> JiraIssueController:
    """Get the Jira issue controller."""
    return JiraIssueController(jira_issue_service)
