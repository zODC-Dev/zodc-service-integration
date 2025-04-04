
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.database import get_db
from src.domain.repositories.jira_issue_history_repository import IJiraIssueHistoryRepository
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService
from src.infrastructure.repositories.sqlalchemy_jira_issue_history_repository import (
    SQLAlchemyJiraIssueHistoryRepository,
)
from src.infrastructure.services.jira_issue_history_database_service import JiraIssueHistoryDatabaseService


async def get_jira_issue_history_repository(
    session: AsyncSession = Depends(get_db)
) -> IJiraIssueHistoryRepository:
    """Get the Jira issue history repository"""
    return SQLAlchemyJiraIssueHistoryRepository(session)


async def get_jira_issue_history_database_service(
    jira_issue_history_repository: IJiraIssueHistoryRepository = Depends(get_jira_issue_history_repository)
) -> IJiraIssueHistoryDatabaseService:
    """Get the Jira issue history database service"""
    return JiraIssueHistoryDatabaseService(jira_issue_history_repository)
