from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.entities.user import User as UserEntity
from src.domain.repositories.user_repository import IUserRepository
from src.domain.services.redis_service import IRedisService
from src.infrastructure.models.user import User as UserModel


class SQLAlchemyUserRepository(IUserRepository):
    def __init__(
        self,
        session: AsyncSession,
        redis_service: IRedisService
    ):
        self.session = session
        self.redis_service = redis_service

    async def get_user_by_id(self, user_id: int) -> Optional[UserEntity]:
        result = await self.session.exec(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.first()
        return self._to_domain(user) if user else None

    async def get_user_by_email(self, email: str) -> Optional[UserEntity]:
        try:
            result = await self.session.exec(
                select(UserModel).where(UserModel.email == email)
            )
            user = result.first()
            return self._to_domain(user) if user else None
        except Exception as e:
            log.error(f"{str(e)}")
            return None

    def _to_domain(self, db_user: UserModel) -> UserEntity:
        """Convert DB model to domain entity"""
        return UserEntity(
            id=db_user.id,
            email=db_user.email,
            user_id=db_user.user_id,
            jira_account_id=db_user.jira_account_id,
            created_at=db_user.created_at,
            is_jira_linked=db_user.is_jira_linked
        )
