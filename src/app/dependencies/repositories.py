from fastapi import Depends

from src.app.dependencies.container import DependencyContainer
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
from src.infrastructure.repositories.sqlalchemy_system_config_repository import SQLAlchemySystemConfigRepository

# Repositories dependencies


def get_jira_user_repository() -> SQLAlchemyJiraUserRepository:
    """Get Jira User repository from container"""
    container = DependencyContainer.get_instance()
    return container.jira_user_repository


def get_refresh_token_repository() -> SQLAlchemyRefreshTokenRepository:
    """Get Refresh Token repository from container"""
    container = DependencyContainer.get_instance()
    return container.refresh_token_repository


def get_jira_project_repository() -> SQLAlchemyJiraProjectRepository:
    """Get Jira Project repository from container"""
    container = DependencyContainer.get_instance()
    return container.project_repository


def get_sync_log_repository() -> SQLAlchemySyncLogRepository:
    """Get Sync Log repository from container"""
    container = DependencyContainer.get_instance()
    return container.sync_log_repository


def get_jira_issue_repository() -> SQLAlchemyJiraIssueRepository:
    """Get Jira Issue repository from container"""
    container = DependencyContainer.get_instance()
    return container.jira_issue_repository


def get_jira_sprint_repository() -> SQLAlchemyJiraSprintRepository:
    """Get Jira Sprint repository from container"""
    container = DependencyContainer.get_instance()
    return container.jira_sprint_repository


def get_jira_issue_history_repository() -> SQLAlchemyJiraIssueHistoryRepository:
    """Get Jira Issue History repository from container"""
    container = DependencyContainer.get_instance()
    return container.issue_history_repository


def get_media_repository() -> SQLAlchemyMediaRepository:
    """Get Media repository from container"""
    container = DependencyContainer.get_instance()
    return container.media_repository


def get_system_config_repository() -> SQLAlchemySystemConfigRepository:
    """Get System Config repository from container"""
    container = DependencyContainer.get_instance()
    return container.system_config_repository


def get_jira_repositories(
    user_repository: SQLAlchemyJiraUserRepository = Depends(get_jira_user_repository),
    project_repository: SQLAlchemyJiraProjectRepository = Depends(get_jira_project_repository),
    issue_repository: SQLAlchemyJiraIssueRepository = Depends(get_jira_issue_repository),
    sprint_repository: SQLAlchemyJiraSprintRepository = Depends(get_jira_sprint_repository),
    issue_history_repository: SQLAlchemyJiraIssueHistoryRepository = Depends(get_jira_issue_history_repository),
):
    """Get all Jira repositories"""
    return {
        "user_repository": user_repository,
        "project_repository": project_repository,
        "issue_repository": issue_repository,
        "sprint_repository": sprint_repository,
        "issue_history_repository": issue_history_repository,
    }
