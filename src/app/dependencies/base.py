from typing import AsyncGenerator

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.database import get_db
from src.domain.services.nats_service import INATSService
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyJiraProjectRepository
from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository
from src.infrastructure.services.nats_service import NATSService


async def get_issue_repository(
    session: AsyncSession = Depends(get_db)
) -> AsyncGenerator[SQLAlchemyJiraIssueRepository, None]:
    """Get issue repository"""
    yield SQLAlchemyJiraIssueRepository(session)


async def get_project_repository(
    session: AsyncSession = Depends(get_db)
) -> AsyncGenerator[SQLAlchemyJiraProjectRepository, None]:
    """Get project repository"""
    yield SQLAlchemyJiraProjectRepository(session)


async def get_sync_log_repository(
    session: AsyncSession = Depends(get_db)
) -> AsyncGenerator[SQLAlchemySyncLogRepository, None]:
    """Get sync log repository"""
    yield SQLAlchemySyncLogRepository(session)


async def get_nats_service() -> AsyncGenerator[INATSService, None]:
    """Get Nats service"""
    service = NATSService()
    await service.connect()
    try:
        yield service
    finally:
        await service.disconnect()
