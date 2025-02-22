from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.user import User, UserWithPassword


class IUserRepository(ABC):
    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        pass

    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass
