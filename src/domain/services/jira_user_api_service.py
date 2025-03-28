from abc import ABC, abstractmethod
from typing import List

from src.domain.models.jira_user import JiraUserModel


class IJiraUserAPIService(ABC):
    @abstractmethod
    async def get_user_by_account_id(self, user_id: int, account_id: str) -> JiraUserModel:
        pass

    @abstractmethod
    async def get_user_by_account_id_with_system_user(self, account_id: str) -> JiraUserModel:
        pass

    @abstractmethod
    async def search_users(self, query: str, max_results: int = 50) -> List[JiraUserModel]:
        pass
