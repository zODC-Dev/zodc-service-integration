from fastapi import APIRouter, HTTPException

from src.app.schemas.requests.jira_sprint import SprintStartRequest
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.jira_project import GetJiraSprintDetailsResponse, GetJiraSprintResponse
from src.app.services.jira_sprint_service import JiraSprintApplicationService
from src.configs.logger import log
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError

router = APIRouter(prefix="/api/v1/sprints", tags=["sprints"])


class JiraSprintController:
    def __init__(self, sprint_service: JiraSprintApplicationService):
        self.sprint_service = sprint_service

    async def get_sprint_by_id(self, sprint_id: int) -> StandardResponse[GetJiraSprintDetailsResponse]:
        """Get sprint details by ID with task counts by status"""
        try:
            sprint, task_count_by_status = await self.sprint_service.get_sprint_details(sprint_id=sprint_id)

            if sprint is None:
                raise HTTPException(status_code=404, detail="Sprint not found")

            return StandardResponse(
                message="Sprint details retrieved successfully",
                data=GetJiraSprintDetailsResponse.from_domain(sprint, task_count_by_status)
            )
        except Exception as e:
            log.error(f"Unexpected error when getting sprint {sprint_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e

    async def get_current_sprint(self, project_key: str) -> StandardResponse[GetJiraSprintResponse]:
        """Get the current sprint in Jira"""
        try:
            current_sprint = await self.sprint_service.get_current_sprint(project_key=project_key)

            if current_sprint is None:
                raise HTTPException(status_code=404, detail="No current sprint found")

            current_sprint.is_current = True
            return StandardResponse(
                message="Current sprint retrieved successfully",
                data=GetJiraSprintResponse.from_domain(current_sprint)
            )
        except Exception as e:
            log.error(f"Unexpected error when getting current sprint: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e

    async def start_sprint(
        self,
        sprint_id: int,
        sprint_data: SprintStartRequest
    ) -> StandardResponse[GetJiraSprintResponse]:
        """Start a sprint in Jira using admin account with optional parameters"""
        try:
            updated_sprint = await self.sprint_service.start_sprint(
                sprint_id=sprint_id,
                start_date=sprint_data.start_date,
                end_date=sprint_data.end_date,
                goal=sprint_data.goal
            )

            log.info(f"Updated sprint: {updated_sprint}")
            if updated_sprint is None:
                raise HTTPException(status_code=404, detail="Sprint not found")

            return StandardResponse(
                message="Sprint started successfully",
                data=GetJiraSprintResponse.from_domain(updated_sprint)
            )
        except JiraAuthenticationError as e:
            log.error(f"Authentication error when starting sprint {sprint_id}: {str(e)}")
            raise HTTPException(status_code=401, detail=str(e)) from e
        except JiraConnectionError as e:
            log.error(f"Connection error when starting sprint {sprint_id}: {str(e)}")
            raise HTTPException(status_code=503, detail=str(e)) from e
        except JiraRequestError as e:
            log.error(f"Request error when starting sprint {sprint_id}: {str(e)}")
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e
        except Exception as e:
            log.error(f"Unexpected error when starting sprint {sprint_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e

    async def end_sprint(self, sprint_id: int) -> StandardResponse[GetJiraSprintResponse]:
        """End a sprint in Jira using admin account"""
        try:
            updated_sprint = await self.sprint_service.end_sprint(sprint_id=sprint_id)
            log.info(f"Updated sprint: {updated_sprint}")
            if updated_sprint is None:
                raise HTTPException(status_code=404, detail="Sprint not found")
            return StandardResponse(
                message="Sprint ended successfully",
                data=GetJiraSprintResponse.from_domain(updated_sprint)
            )
        except JiraAuthenticationError as e:
            log.error(f"Authentication error when ending sprint {sprint_id}: {str(e)}")
            raise HTTPException(status_code=401, detail=str(e)) from e
        except JiraConnectionError as e:
            log.error(f"Connection error when ending sprint {sprint_id}: {str(e)}")
            raise HTTPException(status_code=503, detail=str(e)) from e
        except JiraRequestError as e:
            log.error(f"Request error when ending sprint {sprint_id}: {str(e)}")
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e
        except Exception as e:
            log.error(f"Unexpected error when ending sprint {sprint_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e
