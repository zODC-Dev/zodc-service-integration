from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.user import User, UserCreate, UserUpdate


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
    async def get_all_users(self) -> List[User]:
        """Get all users"""
        pass

    @abstractmethod
    async def create_user(self, user: UserCreate) -> User:
        """Create a new user"""
        pass

    @abstractmethod
    async def update_user(self, user: UserUpdate) -> None:
        """Update a user"""
        pass
