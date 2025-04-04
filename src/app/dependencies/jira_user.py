from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.dependencies.common import get_jira_api_client
from src.configs.database import get_db
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.jira_user_api_service import IJiraUserAPIService
from src.domain.services.jira_user_database_service import IJiraUserDatabaseService
from src.infrastructure.repositories.sqlalchemy_jira_user_repository import SQLAlchemyJiraUserRepository
from src.infrastructure.services.jira_user_api_service import JiraUserAPIService
from src.infrastructure.services.jira_user_database_service import JiraUserDatabaseService


async def get_user_repository(
    session: AsyncSession = Depends(get_db)
) -> IJiraUserRepository:
    """Get Jira user repository with database session"""
    return SQLAlchemyJiraUserRepository(session)


async def get_jira_user_api_service(
    client=Depends(get_jira_api_client)
) -> IJiraUserAPIService:
    """Get Jira user API service"""
    return JiraUserAPIService(client)


async def get_jira_user_database_service(
    user_repository=Depends(get_user_repository)
) -> IJiraUserDatabaseService:
    """Get Jira user database service"""
    return JiraUserDatabaseService(user_repository)
