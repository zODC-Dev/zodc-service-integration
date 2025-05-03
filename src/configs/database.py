from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log

from .settings import settings

engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.DEBUG,
    pool_size=40,
    max_overflow=40,
    pool_timeout=60,
    pool_pre_ping=True,
    pool_recycle=3600,
    isolation_level="READ COMMITTED"
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=True,
    autoflush=True
)

Base = declarative_base()


class AsyncSessionManager:
    """Centralized session management utility for consistent transaction handling"""

    @classmethod
    @asynccontextmanager
    async def session(cls, *, auto_commit: bool = True):
        """Get a session with automatic transaction management.

        Args:
            auto_commit (bool, optional): Whether to automatically commit successful transactions. Defaults to True.

        Usage:
            async with AsyncSessionManager.session() as session:
                # Use session for database operations
                # Automatically commits on success or rolls back on error
        """
        session = AsyncSessionLocal()
        transaction_begun = False
        try:
            # Begin transaction explicitly
            await session.begin()
            transaction_begun = True

            yield session

            # Commit if requested and no exceptions occurred
            if auto_commit and session.is_active:
                await session.commit()
        except Exception:
            # Rollback on error if transaction was started
            if transaction_begun and session.is_active:
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    log.error(f"Error during session rollback: {str(rollback_error)}")
            # Re-raise the original exception
            raise
        finally:
            # Always close the session, but only if it's not in an active transaction
            try:
                if session.is_active:
                    # If we have an active transaction that wasn't committed,
                    # we need to roll it back before closing
                    await session.rollback()
                await session.close()
            except Exception as close_error:
                log.error(f"Error closing database session: {str(close_error)}")


def sqlmodel_session_maker(engine) -> Callable[[], AsyncSession]:
    """Returns a SQLModel session maker function.

    Args:
        engine (_type_): SQLModel engine.

    Returns:
        Callable[[], AsyncSession]: AsyncSession maker function.
    """
    return lambda: AsyncSession(bind=engine, autocommit=False, autoflush=True)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each request.

    Yields:
        AsyncSession: a new database session
    """
    # Use the session manager for consistency
    async with AsyncSessionManager.session() as session:
        yield session


async def init_db() -> None:
    """Init database connection at runtime"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        log.info("Database tables created")


session_maker = sqlmodel_session_maker(engine)
