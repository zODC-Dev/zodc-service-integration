from typing import Optional

from src.configs.logger import log
from src.domain.constants.jira import JiraSprintState
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class JiraSprintApplicationService:
    """Application service for Jira sprint operations"""

    def __init__(
        self,
        jira_sprint_api_service: IJiraSprintAPIService,
        jira_sprint_database_service: IJiraSprintDatabaseService,
        jira_issue_repository: IJiraIssueRepository
    ):
        self.jira_sprint_api_service = jira_sprint_api_service
        self.jira_sprint_database_service = jira_sprint_database_service
        self.jira_issue_repository = jira_issue_repository

    async def start_sprint(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """Start a sprint in Jira using admin account"""
        # Get sprint from database
        sprint = await self.jira_sprint_database_service.get_sprint_by_id(sprint_id=sprint_id)
        if sprint is None:
            return None
        await self.jira_sprint_api_service.start_sprint(sprint_id=sprint.jira_sprint_id)
        sprint.state = JiraSprintState.ACTIVE.value
        return sprint

    async def end_sprint(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """End a sprint in Jira using admin account"""
        # Get sprint from database
        sprint = await self.jira_sprint_database_service.get_sprint_by_id(sprint_id=sprint_id)
        if sprint is None:
            return None

        # End sprint in Jira
        await self.jira_sprint_api_service.end_sprint(sprint_id=sprint.jira_sprint_id)
        sprint.state = JiraSprintState.CLOSED.value

        # Reset is_system_linked flag for all issues in this sprint
        try:
            updated_count = await self.jira_issue_repository.reset_system_linked_for_sprint(sprint_id)
            log.info(f"Reset is_system_linked flag for {updated_count} issues in sprint {sprint_id}")
        except Exception as e:
            log.error(f"Error resetting is_system_linked flag for issues in sprint {sprint_id}: {str(e)}")

        return sprint
