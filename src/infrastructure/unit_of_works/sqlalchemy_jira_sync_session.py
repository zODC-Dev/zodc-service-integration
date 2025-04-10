from types import TracebackType
from typing import Callable, Optional, Type

from sqlmodel.ext.asyncio.session import AsyncSession

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

    async def __aenter__(self):
        """Enter context manager"""
        self.session = self._session_maker()

        # Initialize repositories with session
        self.project_repository = SQLAlchemyJiraProjectRepository(self.session)
        self.issue_repository = SQLAlchemyJiraIssueRepository(self.session)
        self.sprint_repository = SQLAlchemyJiraSprintRepository(self.session)
        self.user_repository = SQLAlchemyJiraUserRepository(self.session)
        self.sync_log_repository = SQLAlchemySyncLogRepository(self.session)
        self.issue_history_repository = SQLAlchemyJiraIssueHistoryRepository(self.session)
        # Start transaction
        await self.session.begin()
        return self

    async def __aexit__(self, exc_type: Optional[Type[Exception]], exc_val: Optional[Exception], exc_tb: Optional[TracebackType]) -> None:
        """Exit context manager"""
        try:
            if exc_type:
                await self.abort()
            else:
                await self.session.commit()
        except Exception:
            await self.abort()
            raise
        finally:
            await self.session.close()

    async def complete(self) -> None:
        """Commit all changes to the database"""
        await self.session.commit()

    async def abort(self) -> None:
        """Rollback all changes to the database"""
        await self.session.rollback()
