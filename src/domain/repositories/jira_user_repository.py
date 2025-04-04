from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.jira_user import JiraUserModel


class IJiraUserRepository(ABC):
    @abstractmethod
    async def create_user(self, user_data: JiraUserDBCreateDTO) -> JiraUserModel:
        pass

    @abstractmethod
    async def update_user(self, user_id: int, user_data: JiraUserDBUpdateDTO) -> JiraUserModel:
        pass

    @abstractmethod
    async def update_user_by_jira_account_id(self, account_id: str, user_data: JiraUserDBUpdateDTO) -> Optional[JiraUserModel]:
        pass

    @abstractmethod
    async def get_user_by_id(self, user_id: int) -> Optional[JiraUserModel]:
        pass

    @abstractmethod
    async def get_user_by_jira_account_id(self, account_id: str) -> Optional[JiraUserModel]:
        pass

    @abstractmethod
    async def get_users_by_project(self, project_key: str) -> List[JiraUserModel]:
        pass

    @abstractmethod
    async def search_users(self, search_term: str) -> List[JiraUserModel]:
        pass

    @abstractmethod
    async def get_all_users(self) -> List[JiraUserModel]:
        pass
