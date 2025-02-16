from typing import List, Optional

from fastapi import HTTPException

from src.domain.constants.jira import JiraIssueType
from src.app.schemas.requests.jira import JiraIssueCreateRequest, JiraIssueUpdateRequest
from src.app.schemas.responses.jira import JiraCreateIssueResponse, JiraProjectResponse, JiraIssueResponse, JiraSprintResponse
from src.app.services.jira_service import JiraApplicationService
from src.configs.logger import log
from src.domain.entities.jira import JiraIssueCreate, JiraIssueUpdate
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError


class JiraController:
    def __init__(self, jira_service: JiraApplicationService):
        self.jira_service = jira_service

    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssueResponse]:
        try:
            log.info(f"User {user_id} is fetching issues for project {project_key}")
            issues = await self.jira_service.get_project_issues(
                user_id=user_id,
                project_key=project_key,
                sprint_id=sprint_id,
                is_backlog=is_backlog,
                issue_type=issue_type,
                search=search,
                limit=limit
            )
            return [JiraIssueResponse(**issue.model_dump()) for issue in issues]
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

    async def get_accessible_projects(self, user_id: int) -> List[JiraProjectResponse]:
        try:
            projects = await self.jira_service.get_accessible_projects(user_id)
            return [JiraProjectResponse(**project.model_dump()) for project in projects]
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
            log.error(f"Unexpected error while fetching Jira projects: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred"
            ) from e

    async def create_issue(self, user_id: int, issue: JiraIssueCreateRequest) -> JiraCreateIssueResponse:
        try:
            # Convert request model to domain model
            domain_issue = JiraIssueCreate(
                project_key=issue.project_key,
                summary=issue.summary,
                description=issue.description,
                issue_type=issue.issue_type,
                priority=issue.priority,
                assignee=issue.assignee,
                labels=issue.labels
            )
            issue_response = await self.jira_service.create_issue(user_id, domain_issue)
            return JiraCreateIssueResponse(**issue_response.model_dump())
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
            log.error(f"Unexpected error while creating Jira issue: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred"
            ) from e

    async def update_issue(
        self,
        user_id: int,
        issue_id: str,
        update: JiraIssueUpdateRequest
    ) -> JiraIssueResponse:
        try:
            # Convert request model to domain model
            domain_update = JiraIssueUpdate(
                assignee=update.assignee,
                status=update.status,
                estimate_points=update.estimate_points,
                actual_points=update.actual_points
            )

            updated_task = await self.jira_service.update_issue(
                user_id=user_id,
                issue_id=issue_id,
                update=domain_update
            )
            return JiraIssueResponse(**updated_task.model_dump())
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
            log.error(f"Unexpected error while updating Jira issue: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred"
            ) from e

    async def get_project_sprints(
        self,
        user_id: int,
        project_id: str,
    ) -> List[JiraSprintResponse]:
        try:
            sprints = await self.jira_service.get_project_sprints(
                user_id=user_id,
                project_id=project_id
            )
            return [JiraSprintResponse(**sprint.model_dump()) for sprint in sprints]
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
            log.error(f"Unexpected error while fetching Jira sprints: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred"
            ) from e
