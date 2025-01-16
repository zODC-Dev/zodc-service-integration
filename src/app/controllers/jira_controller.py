from typing import List, Optional
from fastapi import HTTPException

from src.app.services.jira_service import JiraApplicationService
from src.domain.entities.jira import JiraTask, JiraProject
from src.domain.exceptions.jira_exceptions import (
    JiraConnectionError,
    JiraAuthenticationError,
    JiraRequestError
)
from src.configs.logger import log


class JiraController:
    def __init__(self, jira_service: JiraApplicationService):
        self.jira_service = jira_service

    async def get_project_tasks(
        self,
        user_id: int,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraTask]:
        try:
            return await self.jira_service.get_project_tasks(
                user_id=user_id,
                project_id=project_id,
                status=status,
                limit=limit
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
            log.error(f"Unexpected error while fetching Jira tasks: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred"
            ) from e

    async def get_accessible_projects(self) -> List[JiraProject]:
        try:
            return await self.jira_service.get_accessible_projects()
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
