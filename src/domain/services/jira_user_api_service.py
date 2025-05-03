from abc import ABC, abstractmethod
from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.jira_user import JiraUserModel


class IJiraUserAPIService(ABC):
    @abstractmethod
    async def get_user_by_account_id(
        self,
        session: AsyncSession,
        user_id: int,
        account_id: str
    ) -> Optional[JiraUserModel]:
        pass

    @abstractmethod
    async def get_user_by_account_id_with_admin_auth(self, account_id: str) -> Optional[JiraUserModel]:
        """Get user by account ID using admin credentials"""
        pass

    @abstractmethod
    async def search_users(
        self,
        session: AsyncSession,
        user_id: int,
        query: str,
        max_results: int = 50
    ) -> List[JiraUserModel]:
        pass
