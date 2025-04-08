from fastapi import Depends

from src.configs.database import get_db
from src.domain.repositories.jira_issue_history_repository import IJiraIssueHistoryRepository
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.media_repository import IMediaRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.repositories.workflow_mapping_repository import IWorkflowMappingRepository
from src.domain.unit_of_works.jira_sync_session import IJiraSyncSession
from src.infrastructure.repositories.sqlalchemy_jira_issue_history_repository import (
    SQLAlchemyJiraIssueHistoryRepository,
)
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyJiraProjectRepository
from src.infrastructure.repositories.sqlalchemy_jira_sprint_repository import SQLAlchemyJiraSprintRepository
from src.infrastructure.repositories.sqlalchemy_jira_user_repository import SQLAlchemyJiraUserRepository
from src.infrastructure.repositories.sqlalchemy_media_repository import SQLAlchemyMediaRepository
from src.infrastructure.repositories.sqlalchemy_refresh_token_repository import SQLAlchemyRefreshTokenRepository
from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository
from src.infrastructure.repositories.sqlalchemy_workflow_mapping_repository import SQLAlchemyWorkflowMappingRepository
from src.infrastructure.unit_of_works.sqlalchemy_jira_sync_session import SQLAlchemyJiraSyncSession


async def get_jira_project_repository(session=Depends(get_db)) -> IJiraProjectRepository:
    """Get a project repository instance."""
    return SQLAlchemyJiraProjectRepository(session)


async def get_jira_issue_repository(session=Depends(get_db)) -> IJiraIssueRepository:
    """Get issue repository"""
    return SQLAlchemyJiraIssueRepository(session)


async def get_jira_sprint_repository(session=Depends(get_db)) -> IJiraSprintRepository:
    """Get Jira sprint repository"""
    return SQLAlchemyJiraSprintRepository(session)


async def get_jira_issue_history_repository(session=Depends(get_db)) -> IJiraIssueHistoryRepository:
    """Get a issue history repository instance."""
    return SQLAlchemyJiraIssueHistoryRepository(session)


async def get_jira_user_repository(session=Depends(get_db)) -> IJiraUserRepository:
    """Get the user repository."""
    return SQLAlchemyJiraUserRepository(session=session)


async def get_refresh_token_repository(session=Depends(get_db)) -> IRefreshTokenRepository:
    """Get the refresh token repository."""
    return SQLAlchemyRefreshTokenRepository(session=session)


async def get_media_repository(session=Depends(get_db)) -> IMediaRepository:
    """Get the media repository"""
    return SQLAlchemyMediaRepository(session)


async def get_sync_log_repository(session=Depends(get_db)) -> ISyncLogRepository:
    """Get the sync log repository."""
    return SQLAlchemySyncLogRepository(session)


async def get_workflow_mapping_repository(session=Depends(get_db)) -> IWorkflowMappingRepository:
    """Get the workflow mapping repository"""
    return SQLAlchemyWorkflowMappingRepository(session)


async def get_sqlalchemy_jira_sync_session(session=Depends(get_db)) -> IJiraSyncSession:
    """Get Jira sync session instance."""
    return SQLAlchemyJiraSyncSession(session_maker=session)
