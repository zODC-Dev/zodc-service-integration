from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.user import User, UserUpdate, UserWithPassword


class IUserRepository(ABC):
    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass

    @abstractmethod
    async def get_user_with_password_by_email(self, email: str) -> Optional[UserWithPassword]:
        """Get user by email with password"""
        pass

    @abstractmethod
    async def get_user_by_id_with_role_permissions(self, user_id: int) -> Optional[User]:
        """Get user by ID with role permissions"""
        pass

    @abstractmethod
    async def update_user_by_id(self, user_id: int, user: UserUpdate) -> None:
        """Update user by ID"""
        pass
