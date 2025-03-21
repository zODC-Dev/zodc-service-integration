from typing import Callable

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.services.redis_service import IRedisService
from src.domain.unit_of_works.jira_sync_session import IJiraSyncSession
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyJiraProjectRepository
from src.infrastructure.repositories.sqlalchemy_jira_sprint_repository import SQLAlchemyJiraSprintRepository
from src.infrastructure.repositories.sqlalchemy_jira_user_repository import SQLAlchemyJiraUserRepository
from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository


class SQLAlchemyJiraSyncSession(IJiraSyncSession):
    def __init__(self, session_maker: Callable[[], AsyncSession], redis_service: IRedisService):
        self._session_maker = session_maker
        self.session: AsyncSession = None
        self.project_repository = None
        self.issue_repository = None
        self.sprint_repository = None
        self.user_repository = None
        self.sync_log_repository = None
        self.redis_service = redis_service

    async def __aenter__(self):
        """Enter context manager"""
        self.session = self._session_maker()

        # Initialize repositories with session
        self.project_repository = SQLAlchemyJiraProjectRepository(self.session)
        self.issue_repository = SQLAlchemyJiraIssueRepository(self.session)
        self.sprint_repository = SQLAlchemyJiraSprintRepository(self.session)
        self.user_repository = SQLAlchemyJiraUserRepository(self.session, self.redis_service)
        self.sync_log_repository = SQLAlchemySyncLogRepository(self.session)

        # Start transaction
        await self.session.begin()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
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

    async def complete(self):
        """Commit all changes to the database"""
        await self.session.commit()

    async def abort(self):
        """Rollback all changes to the database"""
        await self.session.rollback()
