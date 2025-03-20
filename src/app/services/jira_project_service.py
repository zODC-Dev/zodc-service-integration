from datetime import datetime, timezone
from typing import List, Optional

from src.domain.constants.jira import JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_project import JiraProjectCreateDTO, JiraProjectModel, JiraProjectUpdateDTO, JiraSprintModel
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_project_database_service import IJiraProjectDatabaseService


class JiraProjectApplicationService:
    def __init__(
        self,
        jira_project_api_service: IJiraProjectAPIService,
        jira_project_db_service: IJiraProjectDatabaseService
    ):
        self.jira_project_api_service = jira_project_api_service
        self.jira_project_db_service = jira_project_db_service

    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        return await self.jira_project_service.get_project_issues(
            user_id=user_id,
            project_key=project_key,
            sprint_id=sprint_id,
            is_backlog=is_backlog,
            issue_type=issue_type,
            search=search,
            limit=limit
        )

    async def get_accessible_projects(self, user_id: int) -> List[JiraProjectModel]:
        """Get projects from database, if not found fetch from API and save"""
        # First try to get from database
        projects = await self.jira_project_db_service.get_all_projects()

        if not projects:
            # If no projects in database, fetch from API
            projects = await self.jira_project_api_service.get_accessible_projects(user_id)

            # Save to database
            for project in projects:
                create_dto = JiraProjectCreateDTO(
                    key=project.key,
                    name=project.name,
                    jira_project_id=project.jira_project_id,
                    last_synced_at=datetime.now(timezone.utc)
                )
                await self.jira_project_db_service.create_project(create_dto)

        return projects

    async def get_project_sprints(
        self,
        user_id: int,
        project_id: str,
    ) -> List[JiraSprintModel]:
        # Sprints are always fetched from API as they're dynamic
        return await self.jira_project_api_service.get_project_sprints(
            user_id=user_id,
            project_id=project_id
        )

    async def get_project_by_key(self, key: str) -> Optional[JiraProjectModel]:
        """Get project from database by key"""
        return await self.jira_project_db_service.get_project_by_key(key)

    async def update_project(
        self,
        project_id: int,
        project_data: JiraProjectUpdateDTO
    ) -> JiraProjectModel:
        """Update project in database"""
        return await self.jira_project_db_service.update_project(project_id, project_data)
