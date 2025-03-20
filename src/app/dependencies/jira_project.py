from fastapi import Depends

from src.app.controllers.jira_project_controller import JiraProjectController
from src.app.dependencies.common import get_redis_service
from src.app.dependencies.jira_user import get_jira_user_repository
from src.app.dependencies.refresh_token import get_token_scheduler_service
from src.app.services.jira_project_service import JiraProjectApplicationService
from src.configs.database import get_db
from src.domain.repositories.jira_project_repository import IProjectRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_project_database_service import IJiraProjectDatabaseService
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_scheduler_service import ITokenSchedulerService
from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyProjectRepository
from src.infrastructure.services.jira_project_api_service import JiraProjectAPIService
from src.infrastructure.services.jira_project_database_service import JiraProjectDatabaseService


def get_jira_project_repository(session=Depends(get_db)) -> IProjectRepository:
    """Get a project repository instance."""
    return SQLAlchemyProjectRepository(session)


def get_jira_project_api_service(
    redis_service: IRedisService = Depends(get_redis_service),
    token_scheduler_service: ITokenSchedulerService = Depends(get_token_scheduler_service),
    user_repository: IJiraUserRepository = Depends(get_jira_user_repository)
) -> IJiraProjectAPIService:
    """Get Jira project API service instance."""
    return JiraProjectAPIService(redis_service, token_scheduler_service, user_repository)


def get_jira_project_db_service(
    project_repository: IProjectRepository = Depends(get_jira_project_repository)
) -> IJiraProjectDatabaseService:
    """Get Jira project database service instance."""
    return JiraProjectDatabaseService(project_repository)


def get_jira_project_application_service(
    api_service: IJiraProjectAPIService = Depends(get_jira_project_api_service),
    db_service: IJiraProjectDatabaseService = Depends(get_jira_project_db_service)
) -> JiraProjectApplicationService:
    """Get Jira project application service instance."""
    return JiraProjectApplicationService(api_service, db_service)


def get_jira_project_controller(
    app_service: JiraProjectApplicationService = Depends(get_jira_project_application_service),
    project_repository: IProjectRepository = Depends(get_jira_project_repository)
) -> JiraProjectController:
    """Get Jira project controller instance."""
    return JiraProjectController(app_service, project_repository)
