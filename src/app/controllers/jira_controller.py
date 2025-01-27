from typing import List, Optional

from fastapi import HTTPException

from src.app.schemas.requests.jira import JiraIssueCreateRequest, JiraTaskUpdateRequest
from src.app.schemas.responses.jira import JiraCreateIssueResponse, JiraProjectResponse, JiraTaskResponse
from src.app.services.jira_service import JiraApplicationService
from src.configs.logger import log
from src.domain.entities.jira import JiraIssueCreate, JiraTaskUpdate
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError


class JiraController:
    def __init__(self, jira_service: JiraApplicationService):
        self.jira_service = jira_service

    async def get_project_tasks(
        self,
        user_id: int,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraTaskResponse]:
        try:
            tasks = await self.jira_service.get_project_tasks(
                user_id=user_id,
                project_id=project_id,
                status=status,
                limit=limit
            )
            return [JiraTaskResponse(**task.model_dump()) for task in tasks]
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
            log.error(f"Unexpected error while fetching Jira tasks: {str(e)}")
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
        update: JiraTaskUpdateRequest
    ) -> JiraTaskResponse:
        try:
            # Convert request model to domain model
            domain_update = JiraTaskUpdate(
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
            return JiraTaskResponse(**updated_task.model_dump())
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
