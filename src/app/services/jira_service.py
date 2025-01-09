from typing import List, Optional

from src.domain.entities.jira import JiraTask
from src.domain.services.jira_service import IJiraService


class JiraApplicationService:
    def __init__(self, jira_service: IJiraService):
        self.jira_service = jira_service

    async def get_project_tasks(
        self,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraTask]:
        return await self.jira_service.get_project_tasks(
            project_id=project_id,
            status=status,
            limit=limit
        )
