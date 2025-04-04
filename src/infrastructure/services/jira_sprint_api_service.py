import asyncio
from typing import List, Optional

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.exceptions.jira_exceptions import JiraRequestError
from src.domain.models.jira.apis.mappers.jira_board import JiraBoardMapper
from src.domain.models.jira.apis.mappers.jira_sprint import JiraSprintMapper
from src.domain.models.jira.apis.responses.jira_board import JiraBoardAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_sprint import JiraSprintAPIGetResponseDTO
from src.domain.models.jira_board import JiraBoardModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.infrastructure.services.jira_service import JiraAPIClient


class JiraSprintAPIService(IJiraSprintAPIService):
    """Service để tương tác với Jira Sprint API"""

    def __init__(self, client: JiraAPIClient):
        self.client = client
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds
        self.system_user_id = settings.JIRA_SYSTEM_USER_ID

    async def get_sprint_by_id_with_system_user(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """Get sprint using system user account"""
        return await self.get_sprint_by_id(self.system_user_id, sprint_id)

    async def get_sprint_by_id(self, user_id: int, sprint_id: int) -> Optional[JiraSprintModel]:
        """Get sprint from Jira API with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                response_data = await self.client.get(
                    f"/rest/agile/1.0/sprint/{sprint_id}",
                    user_id,
                    error_msg=f"Error fetching sprint {sprint_id}"
                )

                log.info(f"Response data when get sprint: {response_data}")

                # Map response to domain model
                sprint: JiraSprintModel = await self.client.map_to_domain(
                    response_data,
                    JiraSprintAPIGetResponseDTO,
                    JiraSprintMapper
                )

                return sprint

            except JiraRequestError as e:
                if e.status_code == 404:
                    log.warning(f"Sprint {sprint_id} not found in Jira")
                    return None
                elif attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # exponential backoff
                    log.warning(f"Retrying get_sprint after {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    log.error(f"Failed to fetch sprint {sprint_id} after {self.retry_attempts} attempts")
                    return None

            except Exception as e:
                log.error(f"Unexpected error fetching sprint {sprint_id}: {str(e)}")
                return None

        return None

    async def get_project_sprints(self, user_id: int, project_key: str) -> List[JiraSprintModel]:
        """Get all sprints for a project"""
        try:
            # First get the board id for the project
            boards_response = await self.client.get(
                "/rest/agile/1.0/board",
                user_id,
                params={"projectKeyOrId": project_key},
                error_msg=f"Error fetching boards for project {project_key}"
            )

            boards = boards_response.get("values", [])
            if not boards:
                log.warning(f"No boards found for project {project_key}")
                return []

            # Use the first board (usually there's only one per project)
            board_id = boards[0]["id"]

            # Get all sprints for the board
            sprints_response = await self.client.get(
                f"/rest/agile/1.0/board/{board_id}/sprint",
                user_id,
                error_msg=f"Error fetching sprints for board {board_id}"
            )

            sprints: List[JiraSprintModel] = []
            for sprint_data in sprints_response.get("values", []):
                sprint: JiraSprintModel = await self.client.map_to_domain(
                    sprint_data,
                    JiraSprintAPIGetResponseDTO,
                    JiraSprintMapper
                )
                sprints.append(sprint)

            return sprints

        except Exception as e:
            log.error(f"Error fetching sprints for project {project_key}: {str(e)}")
            return []

    async def get_board_by_id(self, board_id: int) -> Optional[JiraBoardModel]:
        """Get board information by ID"""
        try:
            response_data = await self.client.get(
                f"/rest/agile/1.0/board/{board_id}",
                self.system_user_id,
                error_msg=f"Error fetching board {board_id}"
            )

            log.info(f"Response data when get board: {response_data}")

            # Method 1: Using DTO and mapper
            try:
                board_dto = JiraBoardAPIGetResponseDTO.model_validate(response_data)
                board_model = JiraBoardMapper.to_domain(board_dto)
                return board_model
            except Exception as e:
                log.error(f"Error mapping board data using DTO: {str(e)}")

                # Method 2: Fallback to direct mapping
                return JiraBoardMapper.from_dict(response_data)

        except Exception as e:
            log.error(f"Error fetching board {board_id}: {str(e)}")
            return None
