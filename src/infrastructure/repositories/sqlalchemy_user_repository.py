from typing import List, Optional

from sqlalchemy import update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.entities.user import User as UserEntity, UserCreate, UserUpdate
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

    async def get_all_users(self) -> List[UserEntity]:
        result = await self.session.exec(
            select(UserModel)
        )
        users = result.all()
        return [self._to_domain(user) for user in users]

    async def create_user(self, user: UserCreate) -> UserEntity:
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(user.email)
            if existing_user:
                raise ValueError("User already exists")

            db_user = UserModel(**user.model_dump())
            self.session.add(db_user)
            await self.session.commit()
            return self._to_domain(db_user)
        except Exception as e:
            log.error(f"Error creating user: {str(e)}")
            raise e

    async def update_user(self, user: UserUpdate) -> None:
        try:
            stmt = (
                update(UserModel).where(UserModel.email == user.email).values(  # type: ignore
                    **user.model_dump(exclude_none=True))
            )
            await self.session.exec(stmt)  # type: ignore
            await self.session.commit()
        except Exception as e:
            log.error(f"Error updating user: {str(e)}")
            raise e

    async def get_user_by_jira_account_id(self, jira_account_id: str) -> Optional[UserEntity]:
        try:
            result = await self.session.exec(
                select(UserModel).where(UserModel.jira_account_id == jira_account_id)
            )
            user = result.first()
            return self._to_domain(user) if user else None
        except Exception as e:
            log.error(f"Error getting user by Jira account ID: {str(e)}")
            return None

    def _to_domain(self, db_user: UserModel) -> UserEntity:
        """Convert DB model to domain entity"""
        return UserEntity(
            id=db_user.id,
            email=db_user.email,
            user_id=db_user.user_id,
            jira_account_id=db_user.jira_account_id,
            is_system_user=db_user.is_system_user,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
