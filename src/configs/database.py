from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log

from .settings import settings

engine = create_async_engine(str(settings.DATABASE_URL), echo=settings.DEBUG)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each request.

    Yields:
        AsyncSession: a new database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Init database connection at runtime"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        log.info("Database tables created")
