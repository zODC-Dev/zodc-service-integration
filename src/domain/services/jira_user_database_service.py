from abc import ABC, abstractmethod
from typing import Optional

from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.jira_user import JiraUserModel


class IJiraUserDatabaseService(ABC):
    @abstractmethod
    async def create_user(self, user_data: JiraUserDBCreateDTO) -> JiraUserModel:
        pass

    @abstractmethod
    async def update_user(self, user_id: str, user_data: JiraUserDBUpdateDTO) -> JiraUserModel:
        pass

    @abstractmethod
    async def get_user_by_account_id(self, account_id: str) -> Optional[JiraUserModel]:
        pass
