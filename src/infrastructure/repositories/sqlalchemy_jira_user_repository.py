from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import col, or_, select

from src.domain.exceptions.user_exceptions import UserCreationError, UserNotFoundError
from src.configs.logger import log
from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.jira_user import JiraUserModel
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.infrastructure.entities.jira_user import JiraUserEntity


class SQLAlchemyJiraUserRepository(IJiraUserRepository):
    """Repository implementation for Jira users using SQLAlchemy"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, user_data: JiraUserDBCreateDTO) -> JiraUserModel:
        """Create a new user in the database"""
        try:
            # Convert DTO to dictionary
            user_dict = user_data.model_dump()

            # Convert datetime objects to timezone-naive for PostgreSQL
            if 'created_at' in user_dict and user_dict['created_at'] and user_dict['created_at'].tzinfo:
                user_dict['created_at'] = user_dict['created_at'].replace(tzinfo=None)
            if 'updated_at' in user_dict and user_dict['updated_at'] and user_dict['updated_at'].tzinfo:
                user_dict['updated_at'] = user_dict['updated_at'].replace(tzinfo=None)

            # Convert DTO to entity
            user_entity = JiraUserEntity(**user_dict)

            # Add to session
            self.session.add(user_entity)
            await self.session.commit()
            await self.session.refresh(user_entity)

            # Convert to domain model
            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            await self.session.rollback()
            log.error(f"Error creating user: {str(e)}")
            raise UserCreationError(f"Error creating user: {str(e)}") from e

    async def update_user(self, user_id: int, user_data: JiraUserDBUpdateDTO) -> JiraUserModel:
        """Update user by ID"""
        try:
            # Get existing user
            result = await self.session.execute(
                select(JiraUserEntity).where(col(JiraUserEntity.user_id) == user_id)
            )
            user_entity = result.scalars().first()

            if not user_entity:
                log.warning(f"User with ID {user_id} not found")
                raise UserNotFoundError(f"User with ID {user_id} not found")

            # Update fields
            update_data = user_data.model_dump(exclude_unset=True)

            # Convert datetime objects to timezone-naive for PostgreSQL
            if 'updated_at' in update_data and update_data['updated_at'] and update_data['updated_at'].tzinfo:
                update_data['updated_at'] = update_data['updated_at'].replace(tzinfo=None)

            for key, value in update_data.items():
                if value is not None:
                    setattr(user_entity, key, value)

            # Commit changes
            await self.session.commit()
            await self.session.refresh(user_entity)

            # Convert to domain model
            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            await self.session.rollback()
            log.error(f"Error updating user: {str(e)}")
            raise

    async def update_user_by_jira_account_id(self, account_id: str, user_data: JiraUserDBUpdateDTO) -> Optional[JiraUserModel]:
        """Update user by Jira account ID"""
        try:
            # Get existing user
            result = await self.session.execute(
                select(JiraUserEntity).where(col(JiraUserEntity.jira_account_id) == account_id)
            )
            user_entity = result.scalars().first()

            if not user_entity:
                log.warning(f"User with account ID {account_id} not found")
                return None

            # Update fields
            update_data = user_data.model_dump(exclude_unset=True)

            # Convert datetime objects to timezone-naive for PostgreSQL
            if 'updated_at' in update_data and update_data['updated_at'] and update_data['updated_at'].tzinfo:
                update_data['updated_at'] = update_data['updated_at'].replace(tzinfo=None)

            for key, value in update_data.items():
                if value is not None:
                    setattr(user_entity, key, value)

            # Commit changes
            await self.session.commit()
            await self.session.refresh(user_entity)

            # Convert to domain model
            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            await self.session.rollback()
            log.error(f"Error updating user by account ID: {str(e)}")
            raise

    async def get_user_by_id(self, user_id: int) -> Optional[JiraUserModel]:
        """Get user by ID"""
        try:
            result = await self.session.execute(
                select(JiraUserEntity).where(col(JiraUserEntity.user_id) == user_id)
            )
            user_entity = result.scalars().first()

            if not user_entity:
                return None

            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            log.error(f"Error getting user by ID: {str(e)}")
            return None

    async def get_user_by_jira_account_id(self, account_id: str) -> Optional[JiraUserModel]:
        """Get user by Jira account ID"""
        try:
            result = await self.session.execute(
                select(JiraUserEntity).where(col(JiraUserEntity.jira_account_id) == account_id)
            )
            user_entity = result.scalars().first()

            if not user_entity:
                return None

            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            log.error(f"Error getting user by account ID: {str(e)}")
            return None

    async def get_users_by_project(self, project_key: str) -> List[JiraUserModel]:
        """Get users associated with a project"""
        try:
            # For now, just return all users
            # In a real implementation, you would have a project-user association
            result = await self.session.execute(
                select(JiraUserEntity)
            )
            user_entities = result.scalars().all()

            return [JiraUserModel.model_validate(user) for user in user_entities]
        except Exception as e:
            log.error(f"Error getting users by project: {str(e)}")
            return []

    async def search_users(self, search_term: str) -> List[JiraUserModel]:
        """Search users by display name or email"""
        try:
            search_pattern = f"%{search_term}%"
            result = await self.session.execute(
                select(JiraUserEntity).where(
                    or_(
                        col(JiraUserEntity.name).ilike(search_pattern),
                        col(JiraUserEntity.email).ilike(search_pattern)
                    )
                )
            )
            user_entities = result.scalars().all()

            return [JiraUserModel.model_validate(user) for user in user_entities]
        except Exception as e:
            log.error(f"Error searching users: {str(e)}")
            return []

    async def get_all_users(self) -> List[JiraUserModel]:
        """Get all users"""
        try:
            result = await self.session.execute(
                select(JiraUserEntity)
            )
            user_entities = result.scalars().all()

            return [JiraUserModel.model_validate(user) for user in user_entities]
        except Exception as e:
            log.error(f"Error getting all users: {str(e)}")
            return []
