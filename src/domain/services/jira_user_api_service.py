from abc import ABC, abstractmethod
from typing import List

from src.domain.models.jira_user import JiraUserModel


class IJiraUserAPIService(ABC):
    @abstractmethod
    async def get_user_details(self, user_id: int, account_id: str) -> JiraUserModel:
        pass

    @abstractmethod
    async def get_project_users(self, user_id: int, project_key: str) -> List[JiraUserModel]:
        pass
