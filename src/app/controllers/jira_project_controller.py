from typing import List, Optional

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_issue import (
    GetJiraIssueResponse,
)
from src.app.schemas.responses.jira_project import (
    GetJiraProjectResponse,
    GetJiraSprintResponse,
)
from src.app.services.jira_project_service import JiraProjectApplicationService
from src.configs.logger import log
from src.domain.constants.jira import JiraIssueType
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class JiraProjectController:
    def __init__(
        self,
        jira_project_service: JiraProjectApplicationService,
        project_repository: IJiraProjectRepository,
        jira_sprint_database_service: IJiraSprintDatabaseService
    ):
        self.jira_project_service = jira_project_service
        self.project_repository = project_repository
        self.jira_sprint_database_service = jira_sprint_database_service

    async def get_project_issues(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: Optional[int] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> StandardResponse[List[GetJiraIssueResponse]]:
        try:
            # Sprint id is system sprint id, not sprint id in Jira

            log.info(f"User {user_id} is fetching issues for project {project_key} from database")
            issues = await self.jira_project_service.get_project_issues(
                session=session,
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id,
                is_backlog=is_backlog,
                issue_type=issue_type,
                search=search,
                limit=limit
            )

            current_sprint: Optional[JiraSprintModel] = None
            if sprint_id:
                current_sprint = await self.jira_sprint_database_service.get_sprint_by_id(session=session, sprint_id=sprint_id)

            return StandardResponse(
                message="Issues fetched successfully from database",
                data=[GetJiraIssueResponse.from_domain(issue, current_sprint) for issue in issues]
            )
        except Exception as e:
            log.error(f"Error fetching issues from database: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch issues from database"
            ) from e

    async def get_projects(
        self,
        session: AsyncSession,
        user_id: int
    ) -> StandardResponse[List[GetJiraProjectResponse]]:
        """Get all accessible projects"""
        try:
            projects = await self.jira_project_service.get_accessible_projects(session=session, user_id=user_id)
            return StandardResponse(
                message="Projects fetched successfully",
                data=[GetJiraProjectResponse.from_domain(p) for p in projects]
            )
        except (JiraAuthenticationError, JiraConnectionError, JiraRequestError) as e:
            log.error(f"Failed to get projects: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Unexpected error getting projects: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error") from e

    async def get_project_sprints(
        self,
        session: AsyncSession,
        project_key: str,
    ) -> StandardResponse[List[GetJiraSprintResponse]]:
        """Get all sprints for a project with current sprint indication"""
        try:
            sprints = await self.jira_project_service.get_project_sprints(session=session, project_key=project_key)

            return StandardResponse(
                message="Sprints fetched successfully",
                data=[GetJiraSprintResponse.from_domain(s) for s in sprints]
            )
        except Exception as e:
            log.error(f"Error getting project sprints: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error getting project sprints: {str(e)}"
            ) from e
