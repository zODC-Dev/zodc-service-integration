from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.jira_user import JiraUserModel
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.jira_user_database_service import IJiraUserDatabaseService


class JiraUserDatabaseService(IJiraUserDatabaseService):
    def __init__(self, user_repository: IJiraUserRepository):
        self.user_repository = user_repository

    async def create_user(self, session: AsyncSession, user_data: JiraUserDBCreateDTO) -> JiraUserModel:
        """Create a new user"""
        try:
            return await self.user_repository.create_user(session, user_data)
        except Exception as e:
            log.error(f"Error creating user: {str(e)}")
            raise

    async def update_user(self, session: AsyncSession, user_id: int, user_data: JiraUserDBUpdateDTO) -> JiraUserModel:
        """Update user by ID"""
        try:
            return await self.user_repository.update_user(session, user_id, user_data)
        except Exception as e:
            log.error(f"Error updating user: {str(e)}")
            raise

    async def update_user_by_jira_account_id(self, session: AsyncSession, jira_account_id: str, user_data: JiraUserDBUpdateDTO) -> JiraUserModel:
        """Update user by Jira account ID"""
        try:
            return await self.user_repository.update_user_by_jira_account_id(session, jira_account_id, user_data)
        except Exception as e:
            log.error(f"Error updating user by account ID: {str(e)}")
            raise

    async def get_user_by_id(self, session: AsyncSession, user_id: int) -> Optional[JiraUserModel]:
        """Get user by ID"""
        try:
            return await self.user_repository.get_user_by_id(session, user_id)
        except Exception as e:
            log.error(f"Error getting user by ID: {str(e)}")
            return None

    async def get_user_by_jira_account_id(self, session: AsyncSession, jira_account_id: str) -> Optional[JiraUserModel]:
        """Get user by Jira account ID"""
        try:
            return await self.user_repository.get_user_by_jira_account_id(session, jira_account_id)
        except Exception as e:
            log.error(f"Error getting user by account ID: {str(e)}")
            return None

    async def get_users_by_project(self, session: AsyncSession, project_key: str) -> List[JiraUserModel]:
        """Get users associated with a project"""
        try:
            return await self.user_repository.get_users_by_project(session, project_key)
        except Exception as e:
            log.error(f"Error getting users by project: {str(e)}")
            return []

    async def search_users(self, session: AsyncSession, search_term: str) -> List[JiraUserModel]:
        """Search users by display name or email"""
        try:
            return await self.user_repository.search_users(session, search_term)
        except Exception as e:
            log.error(f"Error searching users: {str(e)}")
            return []
