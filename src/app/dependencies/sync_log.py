from fastapi import Depends

from src.configs.database import get_db
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository


def get_sync_log_repository(session=Depends(get_db)) -> ISyncLogRepository:
    return SQLAlchemySyncLogRepository(session)
