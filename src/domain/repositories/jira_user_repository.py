from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.jira_user import JiraUserCreateDTO, JiraUserModel, JiraUserUpdateDTO


class IJiraUserRepository(ABC):
    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> Optional[JiraUserModel]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[JiraUserModel]:
        """Get user by email"""
        pass

    @abstractmethod
    async def get_all_users(self) -> List[JiraUserModel]:
        """Get all users"""
        pass

    @abstractmethod
    async def create_user(self, user: JiraUserCreateDTO) -> JiraUserModel:
        """Create a new user"""
        pass

    @abstractmethod
    async def update_user(self, user: JiraUserUpdateDTO) -> None:
        """Update a user"""
        pass

    @abstractmethod
    async def get_user_by_jira_account_id(self, jira_account_id: str) -> Optional[JiraUserModel]:
        """Get user by Jira account ID"""
        pass
