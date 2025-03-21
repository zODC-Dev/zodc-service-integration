from abc import ABC, abstractmethod
from typing import Optional

from src.domain.models.jira_user import JiraUserCreateDTO, JiraUserModel, JiraUserUpdateDTO


class IJiraUserDatabaseService(ABC):
    @abstractmethod
    async def create_user(self, user_data: JiraUserCreateDTO) -> JiraUserModel:
        pass

    @abstractmethod
    async def update_user(self, user_id: str, user_data: JiraUserUpdateDTO) -> JiraUserModel:
        pass

    @abstractmethod
    async def get_user_by_account_id(self, account_id: str) -> Optional[JiraUserModel]:
        pass
