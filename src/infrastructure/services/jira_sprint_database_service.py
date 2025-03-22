from typing import List, Optional

from src.configs.logger import log
from src.domain.models.jira_sprint import JiraSprintCreateDTO, JiraSprintModel, JiraSprintUpdateDTO
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class JiraSprintDatabaseService(IJiraSprintDatabaseService):
    def __init__(self, sprint_repository: IJiraSprintRepository):
        self.sprint_repository = sprint_repository

    async def create_sprint(self, sprint_data: JiraSprintCreateDTO) -> JiraSprintModel:
        return await self.sprint_repository.create_sprint(sprint_data)

    async def update_sprint(self, sprint_id: str, sprint_data: JiraSprintUpdateDTO) -> JiraSprintModel:
        return await self.sprint_repository.update_sprint(sprint_id, sprint_data)

    async def get_sprint_by_id(self, sprint_id: str) -> Optional[JiraSprintModel]:
        return await self.sprint_repository.get_sprint_by_id(sprint_id)

    async def get_project_sprints(self, project_key: str) -> List[JiraSprintModel]:
        log.info(f"Getting sprints for project {project_key}")
        return await self.sprint_repository.get_project_sprints(project_key)
