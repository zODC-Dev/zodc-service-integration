from typing import AsyncGenerator, Callable

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log

from .settings import settings

engine = create_async_engine(str(settings.DATABASE_URL),
                             echo=settings.DEBUG,
                             pool_size=40,
                             max_overflow=40,
                             pool_timeout=60,
                             pool_pre_ping=True,
                             pool_recycle=3600,
                             )

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


def sqlmodel_session_maker(engine) -> Callable[[], AsyncSession]:
    """Returns a SQLModel session maker function.

    Args:
        engine (_type_): SQLModel engine.

    Returns:
        Callable[[], AsyncSession]: AsyncSession maker function.
    """
    return lambda: AsyncSession(bind=engine, autocommit=False, autoflush=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each request.

    Yields:
        AsyncSession: a new database session
    """
    session = AsyncSessionLocal()
    try:
        yield session
    except Exception as e:
        log.error(f"Database session error: {str(e)}")
        await session.rollback()
        raise
    finally:
        try:
            await session.close()
        except Exception as e:
            log.warning(f"Error closing session: {str(e)}")


async def init_db() -> None:
    """Init database connection at runtime"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        log.info("Database tables created")


session_maker = sqlmodel_session_maker(engine)
