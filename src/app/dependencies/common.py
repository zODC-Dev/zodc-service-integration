from typing import AsyncGenerator

from fastapi import Depends
from redis.asyncio import Redis

from src.configs.database import get_db
from src.configs.redis import get_redis_client
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.services.nats_service import INATSService
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_refresh_service import ITokenRefreshService
from src.domain.services.token_scheduler_service import ITokenSchedulerService
from src.infrastructure.repositories.sqlalchemy_jira_user_repository import SQLAlchemyJiraUserRepository
from src.infrastructure.repositories.sqlalchemy_refresh_token_repository import SQLAlchemyRefreshTokenRepository
from src.infrastructure.services.jira_service import JiraAPIClient
from src.infrastructure.services.nats_service import NATSService
from src.infrastructure.services.redis_service import RedisService
from src.infrastructure.services.token_refresh_service import TokenRefreshService
from src.infrastructure.services.token_scheduler_service import TokenSchedulerService


async def get_redis() -> AsyncGenerator[Redis, None]:
    """Dependency for redis client"""
    client = await get_redis_client()
    try:
        yield client
    finally:
        await client.close()


async def get_redis_service(redis_client: Redis = Depends(get_redis_client)):
    """Dependency for redis repository"""
    return RedisService(redis_client=redis_client)


async def get_nats_service() -> INATSService:
    """Dependency for nats service"""
    return NATSService()


def get_jira_user_repository(
    session=Depends(get_db),
) -> IJiraUserRepository:
    """Get the user repository."""
    return SQLAlchemyJiraUserRepository(session=session)


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


async def get_jira_api_client(
    redis_service: RedisService = Depends(get_redis_service),
    token_scheduler_service: ITokenSchedulerService = Depends(get_token_scheduler_service),
):
    """Dependency for jira api client"""
    return JiraAPIClient(
        redis_service=redis_service,
        token_scheduler_service=token_scheduler_service,
    )
