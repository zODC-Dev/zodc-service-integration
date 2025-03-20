from fastapi import Depends

from src.app.dependencies.common import get_redis_service
from src.app.dependencies.jira_user import get_jira_user_repository
from src.configs.database import get_db
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_refresh_service import ITokenRefreshService
from src.infrastructure.repositories.sqlalchemy_refresh_token_repository import SQLAlchemyRefreshTokenRepository
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
    user_repository: IJiraUserRepository = Depends(get_jira_user_repository)
) -> ITokenRefreshService:
    """Get the token refresh service."""
    return TokenRefreshService(refresh_token_repository=refresh_token_repository, redis_service=redis_service, user_repository=user_repository)


def get_token_scheduler_service(
    token_refresh_service: ITokenRefreshService = Depends(get_token_refresh_service),
    refresh_token_repository: IRefreshTokenRepository = Depends(get_refresh_token_repository)
) -> TokenSchedulerService:
    """Get the token scheduler service."""
    return TokenSchedulerService(token_refresh_service=token_refresh_service, refresh_token_repository=refresh_token_repository)
