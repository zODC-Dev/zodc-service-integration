from typing import Optional

from sqlalchemy.orm import selectinload
from sqlmodel import select, update
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.entities.user import User as UserEntity, UserUpdate, UserWithPassword
from src.domain.repositories.user_repository import IUserRepository
from src.domain.services.redis_service import IRedisService
from src.infrastructure.models.user import User as UserModel, UserCreate


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

    async def get_user_by_id_with_role_permissions(self, user_id: int) -> Optional[UserEntity]:
        stmt = (
            select(UserModel)
            .options(selectinload(UserModel.system_role))  # type: ignore
            .where(UserModel.id == int(user_id))
        )
        result = await self.session.exec(stmt)
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

    async def get_user_with_password_by_email(self, email: str) -> Optional[UserWithPassword]:
        try:
            result = await self.session.exec(
                select(UserModel).where(UserModel.email == email)
            )
            user = result.first()
            return self._to_domain_with_password(user) if user else None
        except Exception as e:
            log.error(f"{str(e)}")
            return None

    async def create_user(self, user_data: UserCreate) -> UserEntity:
        user = UserModel.model_validate(user_data)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return self._to_domain(user)

    async def update_user_by_id(self, user_id: int, user: UserUpdate) -> None:
        stmt = (
            update(UserModel).where(UserModel.id == user_id).values(  # type: ignore
                **user.model_dump(exclude={"id"}, exclude_none=True))
        )
        await self.session.exec(stmt)  # type: ignore
        await self.session.commit()

        # clear cache in redis with key user:{user_id}
        await self.redis_service.delete(f"user:{user_id}")

    def _to_domain(self, db_user: UserModel) -> UserEntity:
        """Convert DB model to domain entity"""
        return UserEntity(
            id=db_user.id,
            email=db_user.email,
            name=db_user.name,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            system_role=db_user.system_role,
            is_jira_linked=db_user.is_jira_linked
        )

    def _to_domain_with_password(self, db_user: UserModel) -> UserWithPassword:
        return UserWithPassword(
            id=db_user.id,
            email=db_user.email,
            name=db_user.name,
            is_active=db_user.is_active,
            password=db_user.password,
            is_jira_linked=db_user.is_jira_linked
        )
