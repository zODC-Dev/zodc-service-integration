from fastapi import Depends

from src.app.controllers.jira_issue_controller import JiraIssueController
from src.app.dependencies.common import get_nats_service
from src.app.dependencies.sync_log import get_sync_log_repository
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.database import get_db
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.nats_service import INATSService
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
from src.infrastructure.services.jira_issue_database_service import JiraIssueDatabaseService


def get_jira_issue_repository(
    session=Depends(get_db)
) -> IJiraIssueRepository:
    """Get the Jira issue repository."""
    return SQLAlchemyJiraIssueRepository(session=session)


def get_jira_issue_database_service(
    jira_issue_repository: IJiraIssueRepository = Depends(get_jira_issue_repository)
) -> IJiraIssueDatabaseService:
    """Get the Jira issue service."""
    return JiraIssueDatabaseService(jira_issue_repository)


def get_jira_issue_application_service(
    jira_issue_service: IJiraIssueDatabaseService = Depends(get_jira_issue_database_service),
    jira_issue_repository: IJiraIssueRepository = Depends(get_jira_issue_repository),
    nats_service: INATSService = Depends(get_nats_service),
    sync_log_repository: ISyncLogRepository = Depends(get_sync_log_repository)
) -> JiraIssueApplicationService:
    """Get the Jira issue service."""
    return JiraIssueApplicationService(
        jira_issue_service,
        jira_issue_repository,
        nats_service,
        sync_log_repository
    )


def get_jira_issue_controller(
    jira_issue_service: JiraIssueApplicationService = Depends(get_jira_issue_application_service)
) -> JiraIssueController:
    """Get the Jira issue controller."""
    return JiraIssueController(jira_issue_service)
