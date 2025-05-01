from types import TracebackType
from typing import Callable, Optional, Type

from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.unit_of_works.jira_sync_session import IJiraSyncSession
from src.infrastructure.repositories.sqlalchemy_jira_issue_history_repository import (
    SQLAlchemyJiraIssueHistoryRepository,
)
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyJiraProjectRepository
from src.infrastructure.repositories.sqlalchemy_jira_sprint_repository import SQLAlchemyJiraSprintRepository
from src.infrastructure.repositories.sqlalchemy_jira_user_repository import SQLAlchemyJiraUserRepository
from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository


class SQLAlchemyJiraSyncSession(IJiraSyncSession):
    def __init__(self, session_maker: Callable[[], AsyncSession]):
        self._session_maker = session_maker
        self.session: Optional[AsyncSession] = None
        self.repositories_initialized = False

    async def __aenter__(self):
        """Enter context manager"""
        if self.session is None:
            self.session = self._session_maker()

            # Initialize repositories with session
            self.project_repository = SQLAlchemyJiraProjectRepository(self.session)
            self.issue_repository = SQLAlchemyJiraIssueRepository(self.session)
            self.sprint_repository = SQLAlchemyJiraSprintRepository(self.session)
            self.user_repository = SQLAlchemyJiraUserRepository(self.session)
            self.sync_log_repository = SQLAlchemySyncLogRepository(self.session)
            self.issue_history_repository = SQLAlchemyJiraIssueHistoryRepository(self.session)
            self.repositories_initialized = True

            # Start transaction
            await self.session.begin()

        return self

    async def __aexit__(self, exc_type: Optional[Type[Exception]], exc_val: Optional[Exception], exc_tb: Optional[TracebackType]) -> None:
        """Exit context manager"""
        if not self.session:
            return

        try:
            if exc_type:
                # If there was an exception, roll back the transaction
                await self.abort()
            else:
                # Otherwise, commit the transaction
                await self.complete()
        except Exception as e:
            log.error(f"Error during transaction completion: {str(e)}")
            # Attempt rollback on error during commit
            try:
                await self.abort()
            except Exception as rollback_error:
                log.error(f"Failed to rollback transaction: {str(rollback_error)}")
            raise
        finally:
            try:
                # Only close if we're not in an active transaction
                if hasattr(self.session, 'is_active') and not self.session.is_active:
                    await self.session.close()
                    self.session = None
                    self.repositories_initialized = False
            except Exception as e:
                log.warning(f"Error closing session in unit of work: {str(e)}")
                self.session = None
                self.repositories_initialized = False

    async def complete(self) -> None:
        """Commit all changes to the database"""
        if self.session and self.session.is_active:
            await self.session.commit()

    async def abort(self) -> None:
        """Rollback all changes to the database"""
        if self.session and self.session.is_active:
            await self.session.rollback()
