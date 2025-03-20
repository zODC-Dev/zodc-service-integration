from typing import List, Optional

from sqlalchemy import update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.jira_user import JiraUserCreateDTO, JiraUserModel, JiraUserUpdateDTO
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.redis_service import IRedisService
from src.infrastructure.entities.jira_user import JiraUserEntity


class SQLAlchemyUserRepository(IJiraUserRepository):
    def __init__(
        self,
        session: AsyncSession,
        redis_service: IRedisService
    ):
        self.session = session
        self.redis_service = redis_service

    async def get_user_by_id(self, user_id: int) -> Optional[JiraUserModel]:
        result = await self.session.exec(
            select(JiraUserEntity).where(JiraUserEntity.id == user_id)
        )
        user = result.first()
        return self._to_domain(user) if user else None

    async def get_user_by_email(self, email: str) -> Optional[JiraUserModel]:
        try:
            result = await self.session.exec(
                select(JiraUserEntity).where(JiraUserEntity.email == email)
            )
            user = result.first()
            return self._to_domain(user) if user else None
        except Exception as e:
            log.error(f"{str(e)}")
            return None

    async def get_all_users(self) -> List[JiraUserModel]:
        result = await self.session.exec(
            select(JiraUserEntity)
        )
        users = result.all()
        return [self._to_domain(user) for user in users]

    async def create_user(self, user: JiraUserCreateDTO) -> JiraUserModel:
        try:
            # Check if user already exists
            existing_user = await self.get_user_by_email(user.email)
            if existing_user:
                raise ValueError("User already exists")

            db_user = JiraUserEntity(**user.model_dump())
            self.session.add(db_user)
            await self.session.commit()
            return self._to_domain(db_user)
        except Exception as e:
            log.error(f"Error creating user: {str(e)}")
            raise e

    async def update_user(self, user: JiraUserUpdateDTO) -> None:
        try:
            stmt = (
                update(JiraUserEntity).where(JiraUserEntity.email == user.email).values(  # type: ignore
                    **user.model_dump(exclude_none=True))
            )
            await self.session.exec(stmt)  # type: ignore
            await self.session.commit()
        except Exception as e:
            log.error(f"Error updating user: {str(e)}")
            raise e

    async def get_user_by_jira_account_id(self, jira_account_id: str) -> Optional[JiraUserModel]:
        try:
            result = await self.session.exec(
                select(JiraUserEntity).where(JiraUserEntity.jira_account_id == jira_account_id)
            )
            user = result.first()
            return self._to_domain(user) if user else None
        except Exception as e:
            log.error(f"Error getting user by Jira account ID: {str(e)}")
            return None

    def _to_domain(self, db_user: JiraUserEntity) -> JiraUserModel:
        """Convert DB model to domain entity"""
        return JiraUserModel(
            id=db_user.id,
            email=db_user.email,
            user_id=db_user.user_id,
            jira_account_id=db_user.jira_account_id,
            is_system_user=db_user.is_system_user,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
