from fastapi import Depends

from src.app.controllers.jira_controller import JiraController
from src.app.dependencies.common import get_redis_service
from src.app.dependencies.project import get_project_repository
from src.app.dependencies.user import get_user_repository
from src.app.services.jira_service import JiraApplicationService
from src.configs.database import get_db
from src.domain.repositories.project_repository import IProjectRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.repositories.user_repository import IUserRepository
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_refresh_service import ITokenRefreshService
from src.infrastructure.repositories.sqlalchemy_refresh_token_repository import SQLAlchemyRefreshTokenRepository
from src.infrastructure.services.jira_service import JiraService
from src.infrastructure.services.token_refresh_service import TokenRefreshService
from src.infrastructure.services.token_scheduler_service import TokenSchedulerService


def get_refresh_token_repository(
    session=Depends(get_db)
) -> IRefreshTokenRepository:
    """Get the refresh token repository."""
    return SQLAlchemyRefreshTokenRepository(session=session)


def get_token_refresh_service(
    refresh_token_repository: IRefreshTokenRepository = Depends(get_refresh_token_repository),
    redis_service: IRedisService = Depends(get_redis_service),
    user_repository: IUserRepository = Depends(get_user_repository)
) -> ITokenRefreshService:
    """Get the token refresh service."""
    return TokenRefreshService(refresh_token_repository=refresh_token_repository, redis_service=redis_service, user_repository=user_repository)


def get_token_scheduler_service(
    token_refresh_service: ITokenRefreshService = Depends(get_token_refresh_service),
    refresh_token_repository: IRefreshTokenRepository = Depends(get_refresh_token_repository)
) -> TokenSchedulerService:
    """Get the token scheduler service."""
    return TokenSchedulerService(token_refresh_service=token_refresh_service, refresh_token_repository=refresh_token_repository)


def get_jira_service(
    redis_service: IRedisService = Depends(get_redis_service),
    token_scheduler_service: TokenSchedulerService = Depends(get_token_scheduler_service)
) -> JiraService:
    """Get the Jira service."""
    return JiraService(redis_service=redis_service, token_scheduler_service=token_scheduler_service)


def get_jira_application_service(
    jira_service: JiraService = Depends(get_jira_service)
) -> JiraApplicationService:
    """Get the Jira application service."""
    return JiraApplicationService(jira_service=jira_service)


def get_jira_controller(
    jira_service: JiraApplicationService = Depends(get_jira_service),
    project_repository: IProjectRepository = Depends(get_project_repository)
) -> JiraController:
    """Get the Jira controller."""
    return JiraController(
        jira_service=jira_service,
        project_repository=project_repository
    )
