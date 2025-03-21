from datetime import datetime, timezone
from typing import List, Optional

from src.domain.models.jira_project import JiraProjectCreateDTO, JiraProjectModel, JiraProjectUpdateDTO
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.services.jira_project_database_service import IJiraProjectDatabaseService


class JiraProjectDatabaseService(IJiraProjectDatabaseService):
    def __init__(self, project_repository: IJiraProjectRepository):
        self.project_repository = project_repository

    async def get_project(self, project_id: int) -> Optional[JiraProjectModel]:
        return await self.project_repository.get_project_by_id(project_id)

    async def get_project_by_key(self, key: str) -> Optional[JiraProjectModel]:
        return await self.project_repository.get_project_by_key(key)

    async def get_all_projects(self) -> List[JiraProjectModel]:
        return await self.project_repository.get_all_projects()

    async def create_project(self, project_data: JiraProjectCreateDTO) -> JiraProjectModel:
        project_data.last_synced_at = datetime.now(timezone.utc)
        return await self.project_repository.create_project(project_data)

    async def update_project(
        self,
        project_id: int,
        project_data: JiraProjectUpdateDTO
    ) -> JiraProjectModel:
        return await self.project_repository.update_project(project_id, project_data)

    async def delete_project(self, project_id: int) -> None:
        await self.project_repository.delete_project(project_id)
