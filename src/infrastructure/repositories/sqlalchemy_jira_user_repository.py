from typing import List, Optional

from sqlmodel import col, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.exceptions.user_exceptions import UserCreationError, UserNotFoundError, UserUpdateError
from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.jira_user import JiraUserModel
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.infrastructure.entities.jira_user import JiraUserEntity


class SQLAlchemyJiraUserRepository(IJiraUserRepository):
    """Repository implementation for Jira users using SQLAlchemy"""

    def __init__(self):
        pass

    async def create_user(self, session: AsyncSession, user_data: JiraUserDBCreateDTO) -> JiraUserModel:
        """Create a new user in the database"""
        try:
            # Convert DTO to dictionary
            log.debug(f"Creating user: {user_data}")

            if user_data.email is None or user_data.email == "":
                raise ValueError("Email is required")

            # Check if user already exists if email or jira_account_id or user_id is not None
            conditions = []
            if user_data.email and user_data.email != "":
                conditions.append(col(JiraUserEntity.email) == user_data.email)
            if user_data.jira_account_id and user_data.jira_account_id != "":
                conditions.append(col(JiraUserEntity.jira_account_id) == user_data.jira_account_id)
            if user_data.user_id and user_data.user_id != 0:
                conditions.append(col(JiraUserEntity.user_id) == user_data.user_id)

            if conditions:
                stmt = select(JiraUserEntity).where(or_(*conditions))
            else:
                stmt = select(JiraUserEntity).where(False)
            result = await session.exec(stmt)
            existing_user = result.first()
            if existing_user:
                log.debug(f"User already exists: {existing_user} conditions: {conditions}")
                return JiraUserModel.model_validate(existing_user)

            user_dict = user_data.model_dump()

            # Convert datetime objects to timezone-naive for PostgreSQL
            if 'created_at' in user_dict and user_dict['created_at'] and user_dict['created_at'].tzinfo:
                user_dict['created_at'] = user_dict['created_at'].replace(tzinfo=None)
            if 'updated_at' in user_dict and user_dict['updated_at'] and user_dict['updated_at'].tzinfo:
                user_dict['updated_at'] = user_dict['updated_at'].replace(tzinfo=None)

            # Convert DTO to entity
            user_entity = JiraUserEntity(**user_dict)

            # Add to session
            session.add(user_entity)
            # Let the session manager handle the transaction
            await session.flush()
            await session.refresh(user_entity)

            # Convert to domain model
            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            # Let the session manager handle rollbacks
            log.error(f"Error creating user: {str(e)}")
            raise UserCreationError(f"Error creating user: {str(e)}") from e

    async def update_user(self, session: AsyncSession, user_id: int, user_data: JiraUserDBUpdateDTO) -> JiraUserModel:
        """Update user by ID"""
        try:
            # Get existing user
            result = await session.exec(
                select(JiraUserEntity).where(col(JiraUserEntity.user_id) == user_id)
            )
            user_entity = result.first()

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

            session.add(user_entity)
            # Let the session manager handle the transaction
            await session.flush()
            await session.refresh(user_entity)

            # Convert to domain model
            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            # Let the session manager handle rollbacks
            log.error(f"Error updating user: {str(e)}")
            raise

    async def update_user_by_jira_account_id(self, session: AsyncSession, jira_account_id: str, user_data: JiraUserDBUpdateDTO) -> JiraUserModel:
        """Update user by Jira account ID"""
        try:
            # Get existing user
            result = await session.exec(
                select(JiraUserEntity).where(col(JiraUserEntity.jira_account_id) == jira_account_id)
            )
            user_entity = result.first()

            if not user_entity:
                raise UserNotFoundError(f"User with account ID {jira_account_id} not found")

            # Update fields
            update_data = user_data.model_dump(exclude_unset=True)

            # Convert datetime objects to timezone-naive for PostgreSQL
            if 'updated_at' in update_data and update_data['updated_at'] and update_data['updated_at'].tzinfo:
                update_data['updated_at'] = update_data['updated_at'].replace(tzinfo=None)

            for key, value in update_data.items():
                if value is not None:
                    setattr(user_entity, key, value)

            # Commit changes
            session.add(user_entity)
            # Let the session manager handle the transaction
            await session.flush()
            await session.refresh(user_entity)

            # Convert to domain model
            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            # Let the session manager handle rollbacks
            log.error(f"Error updating user by account ID: {str(e)}")
            raise UserUpdateError(f"Error updating user by account ID: {str(e)}") from e

    async def get_user_by_id(self, session: AsyncSession, user_id: int) -> Optional[JiraUserModel]:
        """Get user by ID"""
        try:
            result = await session.exec(
                select(JiraUserEntity).where(col(JiraUserEntity.user_id) == user_id)
            )
            user_entity = result.first()

            if not user_entity:
                return None

            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            log.error(f"Error getting user by ID: {str(e)}")
            return None

    async def get_user_by_jira_account_id(self, session: AsyncSession, jira_account_id: str) -> Optional[JiraUserModel]:
        """Get user by Jira account ID"""
        try:
            result = await session.exec(
                select(JiraUserEntity).where(col(JiraUserEntity.jira_account_id) == jira_account_id)
            )
            user_entity = result.first()

            if not user_entity:
                return None

            return JiraUserModel.model_validate(user_entity)
        except Exception as e:
            log.error(f"Error getting user by account ID: {str(e)}")
            return None

    async def get_users_by_project(self, session: AsyncSession, project_key: str) -> List[JiraUserModel]:
        """Get users associated with a project"""
        try:
            # For now, just return all users
            # In a real implementation, you would have a project-user association
            result = await session.exec(
                select(JiraUserEntity)
            )
            user_entities = result.all()

            return [JiraUserModel.model_validate(user) for user in user_entities]
        except Exception as e:
            log.error(f"Error getting users by project: {str(e)}")
            return []

    async def search_users(self, session: AsyncSession, search_term: str) -> List[JiraUserModel]:
        """Search users by display name or email"""
        try:
            search_pattern = f"%{search_term}%"
            result = await session.exec(
                select(JiraUserEntity).where(
                    or_(
                        col(JiraUserEntity.name).ilike(search_pattern),
                        col(JiraUserEntity.email).ilike(search_pattern)
                    )
                )
            )
            user_entities = result.all()

            return [JiraUserModel.model_validate(user) for user in user_entities]
        except Exception as e:
            log.error(f"Error searching users: {str(e)}")
            return []

    async def get_all_users(self, session: AsyncSession) -> List[JiraUserModel]:
        """Get all users"""
        try:
            result = await session.exec(
                select(JiraUserEntity)
            )
            user_entities = result.all()

            return [JiraUserModel.model_validate(user) for user in user_entities]
        except Exception as e:
            log.error(f"Error getting all users: {str(e)}")
            return []
