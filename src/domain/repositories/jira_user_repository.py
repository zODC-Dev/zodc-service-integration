from abc import ABC, abstractmethod
from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.jira_user import JiraUserModel


class IJiraUserRepository(ABC):
    @abstractmethod
    async def create_user(self, session: AsyncSession, user_data: JiraUserDBCreateDTO) -> JiraUserModel:
        pass

    @abstractmethod
    async def update_user(self, session: AsyncSession, user_id: int, user_data: JiraUserDBUpdateDTO) -> JiraUserModel:
        pass

    @abstractmethod
    async def update_user_by_jira_account_id(self, session: AsyncSession, jira_account_id: str, user_data: JiraUserDBUpdateDTO) -> JiraUserModel:
        pass

    @abstractmethod
    async def get_user_by_id(self, session: AsyncSession, user_id: int) -> Optional[JiraUserModel]:
        pass

    @abstractmethod
    async def get_user_by_jira_account_id(self, session: AsyncSession, jira_account_id: str) -> Optional[JiraUserModel]:
        pass

    @abstractmethod
    async def get_users_by_project(self, session: AsyncSession, project_key: str) -> List[JiraUserModel]:
        pass

    @abstractmethod
    async def search_users(self, session: AsyncSession, search_term: str) -> List[JiraUserModel]:
        pass

    @abstractmethod
    async def get_all_users(self, session: AsyncSession) -> List[JiraUserModel]:
        pass
