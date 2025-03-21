from abc import ABC, abstractmethod

from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository


class IJiraSyncSession(ABC):
    project_repository: IJiraProjectRepository
    issue_repository: IJiraIssueRepository
    sprint_repository: IJiraSprintRepository
    user_repository: IJiraUserRepository
    sync_log_repository: ISyncLogRepository

    @abstractmethod
    async def __aenter__(self):
        """Enter context manager"""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager"""
        pass

    @abstractmethod
    async def complete(self):
        """Complete the sync session successfully"""
        pass

    @abstractmethod
    async def abort(self):
        """Abort the sync session due to error"""
        pass
