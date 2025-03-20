from typing import List, Optional

from fastapi import HTTPException

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
from src.domain.repositories.jira_project_repository import IProjectRepository


class JiraProjectController:
    def __init__(
        self,
        jira_project_service: JiraProjectApplicationService,
        project_repository: IProjectRepository
    ):
        self.jira_project_service = jira_project_service
        self.project_repository = project_repository

    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> StandardResponse[List[GetJiraIssueResponse]]:
        try:
            log.info(f"User {user_id} is fetching issues for project {project_key}")
            issues = await self.jira_project_service.get_project_issues(
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id,
                is_backlog=is_backlog,
                issue_type=issue_type,
                search=search,
                limit=limit
            )
            return StandardResponse(
                message="Issues fetched successfully",
                data=[GetJiraIssueResponse(**issue.model_dump()) for issue in issues]
            )
        except JiraAuthenticationError as e:
            log.error(f"Jira authentication failed: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail="Failed to authenticate with Jira"
            ) from e
        except JiraConnectionError as e:
            log.error(f"Failed to connect to Jira: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail="Jira service is currently unavailable"
            ) from e
        except JiraRequestError as e:
            log.error(f"Jira request failed: {str(e)}")
            raise HTTPException(
                status_code=e.status_code,
                detail=e.message
            ) from e
        except Exception as e:
            log.error(f"Unexpected error while fetching Jira issues: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred"
            ) from e

    async def get_projects(self, user_id: int) -> StandardResponse[List[GetJiraProjectResponse]]:
        """Get all accessible projects"""
        try:
            projects = await self.jira_project_service.get_accessible_projects(user_id)
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
        user_id: int,
        project_id: str
    ) -> StandardResponse[List[GetJiraSprintResponse]]:
        """Get all sprints in a project"""
        try:
            sprints = await self.jira_project_service.get_project_sprints(user_id, project_id)
            return StandardResponse(
                data=[GetJiraSprintResponse.from_domain(s) for s in sprints]
            )
        except (JiraAuthenticationError, JiraConnectionError, JiraRequestError) as e:
            log.error(f"Failed to get sprints: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            log.error(f"Unexpected error getting sprints: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error") from e
