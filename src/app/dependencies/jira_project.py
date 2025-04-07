from typing import AsyncGenerator

from fastapi import Depends

from src.app.dependencies.jira_issue import get_jira_issue_database_service
from src.app.controllers.jira_project_controller import JiraProjectController
from src.app.dependencies.base import get_project_repository
from src.app.dependencies.common import (
    get_jira_api_client,
    get_jira_user_repository,
)
from src.app.dependencies.jira_sprint import get_jira_sprint_database_service
from src.app.dependencies.sync_log import get_sync_log_repository
from src.app.services.jira_project_service import JiraProjectApplicationService
from src.configs.database import get_db
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_project_database_service import IJiraProjectDatabaseService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService
from src.domain.unit_of_works.jira_sync_session import IJiraSyncSession
from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyJiraProjectRepository
from src.infrastructure.services.jira_project_api_service import JiraProjectAPIService
from src.infrastructure.services.jira_project_database_service import JiraProjectDatabaseService
from src.infrastructure.services.jira_service import JiraAPIClient
from src.infrastructure.unit_of_works.sqlalchemy_jira_sync_session import SQLAlchemyJiraSyncSession


def get_sqlalchemy_jira_sync_session(
    session=Depends(get_db)
) -> IJiraSyncSession:
    """Get Jira sync session instance."""
    return SQLAlchemyJiraSyncSession(session_maker=session)


def get_jira_project_repository(session=Depends(get_db)) -> IJiraProjectRepository:
    """Get a project repository instance."""
    return SQLAlchemyJiraProjectRepository(session)


def get_jira_project_api_service(
    jira_api_client: JiraAPIClient = Depends(get_jira_api_client),
    user_repository: IJiraUserRepository = Depends(get_jira_user_repository)
) -> IJiraProjectAPIService:
    """Get Jira project API service instance."""
    return JiraProjectAPIService(jira_api_client, user_repository)


async def get_jira_project_database_service(
    project_repository=Depends(get_project_repository)
) -> AsyncGenerator[IJiraProjectDatabaseService, None]:
    """Get Jira project database service instance."""
    yield JiraProjectDatabaseService(project_repository)


def get_jira_project_application_service(
    jira_project_api_service: IJiraProjectAPIService = Depends(get_jira_project_api_service),
    jira_project_db_service: IJiraProjectDatabaseService = Depends(get_jira_project_database_service),
    jira_issue_db_service: IJiraIssueDatabaseService = Depends(get_jira_issue_database_service),
    jira_sprint_db_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service),
    sync_session: IJiraSyncSession = Depends(get_sqlalchemy_jira_sync_session),
    sync_log_repository: ISyncLogRepository = Depends(get_sync_log_repository)
) -> JiraProjectApplicationService:
    """Get Jira project application service instance."""
    return JiraProjectApplicationService(
        jira_project_api_service,
        jira_project_db_service,
        jira_issue_db_service,
        jira_sprint_db_service,
        sync_session,
        sync_log_repository
    )


def get_jira_project_controller(
    app_service: JiraProjectApplicationService = Depends(get_jira_project_application_service),
    project_repository: IJiraProjectRepository = Depends(get_jira_project_repository),
    jira_sprint_db_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service)
) -> JiraProjectController:
    """Get Jira project controller instance."""
    return JiraProjectController(app_service, project_repository, jira_sprint_db_service)
