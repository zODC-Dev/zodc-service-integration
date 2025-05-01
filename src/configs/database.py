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
    session = AsyncSessionLocal()
    try:
        # Begin a transaction explicitly
        await session.begin()
        yield session
        # If we get here without exception, commit the transaction
        if session.is_active:
            await session.commit()
    except Exception as e:
        log.error(f"Database session error: {str(e)}")
        # Attempt to rollback if we're in a transaction
        if hasattr(session, 'is_active') and session.is_active:
            await session.rollback()
        raise
    finally:
        try:
            # Only close if not in an active transaction
            if hasattr(session, 'is_active') and not session.is_active:
                await session.close()
        except Exception as e:
            log.warning(f"Error closing session: {str(e)}")


async def init_db() -> None:
    """Init database connection at runtime"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        log.info("Database tables created")


session_maker = sqlmodel_session_maker(engine)
