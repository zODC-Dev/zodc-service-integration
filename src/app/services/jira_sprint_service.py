from typing import Optional

from src.domain.constants.jira import JiraSprintState
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class JiraSprintApplicationService:
    """Application service for Jira sprint operations"""

    def __init__(self, jira_sprint_api_service: IJiraSprintAPIService, jira_sprint_database_service: IJiraSprintDatabaseService):
        self.jira_sprint_api_service = jira_sprint_api_service
        self.jira_sprint_database_service = jira_sprint_database_service

    async def start_sprint(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """Start a sprint in Jira using admin account"""
        # Get sprint from database
        sprint = await self.jira_sprint_database_service.get_sprint_by_id(sprint_id=sprint_id)
        if sprint is None:
            return None
        await self.jira_sprint_api_service.start_sprint(sprint_id=sprint.jira_sprint_id)
        sprint.state = JiraSprintState.ACTIVE
        return sprint

    async def end_sprint(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """End a sprint in Jira using admin account"""
        # Get sprint from database
        sprint = await self.jira_sprint_database_service.get_sprint_by_id(sprint_id=sprint_id)
        if sprint is None:
            return None
        await self.jira_sprint_api_service.end_sprint(sprint_id=sprint.jira_sprint_id)
        sprint.state = JiraSprintState.CLOSED
        return sprint
