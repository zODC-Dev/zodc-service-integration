
from fastapi import Depends

from src.app.dependencies.common import get_redis_service
from src.configs.database import get_db
from src.domain.repositories.user_repository import IUserRepository
from src.domain.services.redis_service import IRedisService
from src.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository


def get_user_repository(
    session=Depends(get_db),
    redis_service: IRedisService = Depends(get_redis_service)
) -> IUserRepository:
    """Get the user repository."""
    return SQLAlchemyUserRepository(session=session, redis_service=redis_service)
