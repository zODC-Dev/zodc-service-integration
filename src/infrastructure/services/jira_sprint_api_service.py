import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

from src.configs.logger import log
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

    def __init__(self, client: JiraAPIClient, admin_client: Optional[JiraAPIClient] = None):
        self.client = client
        self.admin_client = admin_client
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds

    async def get_sprint_by_id_with_admin_auth(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """Get sprint using admin auth"""
        # Sử dụng admin client hoặc client thường với admin auth
        client_to_use = self.admin_client or self.client

        # Gọi API với admin client
        for attempt in range(self.retry_attempts):
            try:
                response_data = await client_to_use.get(
                    f"/rest/agile/1.0/sprint/{sprint_id}",
                    None,  # Không cần user_id
                    error_msg=f"Error fetching sprint {sprint_id}"
                )

                log.info(f"Response data when get sprint: {response_data}")

                # Map response to domain model
                sprint: JiraSprintModel = await client_to_use.map_to_domain(
                    response_data,
                    JiraSprintAPIGetResponseDTO,
                    JiraSprintMapper
                )
                log.info(f"Sprint: {sprint}")

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
            # Sử dụng admin client thay vì system user ID
            client_to_use = self.admin_client or self.client

            response_data = await client_to_use.get(
                f"/rest/agile/1.0/board/{board_id}",
                None,  # Không cần user_id khi sử dụng admin auth
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

    async def start_sprint(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """Start a sprint in Jira"""
        log.info(f"Starting sprint {sprint_id}")

        for attempt in range(self.retry_attempts):
            try:
                start_date = datetime.now().isoformat()
                end_date = (datetime.now() + timedelta(days=14)).isoformat()
                payload = {
                    "state": "active",
                    "startDate": start_date,
                    "endDate": end_date
                }
                # Call Jira API to start the sprint
                await self.client.post(
                    f"/rest/agile/1.0/sprint/{sprint_id}",
                    None,
                    data=payload,
                    error_msg=f"Error starting sprint {sprint_id}"
                )

                # Get the updated sprint data
                return await self.get_sprint_by_id_with_admin_auth(sprint_id)

            except JiraRequestError as e:
                if e.status_code == 404:
                    log.warning(f"Sprint {sprint_id} not found in Jira")
                    return None
                elif attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # exponential backoff
                    log.warning(f"Retrying start_sprint after {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    log.error(f"Failed to start sprint {sprint_id} after {self.retry_attempts} attempts")
                    return None

            except Exception as e:
                log.error(f"Unexpected error starting sprint {sprint_id}: {str(e)}")
                return None

        return None

    async def end_sprint(self, sprint_id: int) -> Optional[JiraSprintModel]:
        """End a sprint in Jira"""
        log.info(f"Ending sprint {sprint_id}")

        for attempt in range(self.retry_attempts):
            try:
                # Call Jira API to end the sprint
                payload = {
                    "state": "closed"
                }
                await self.client.post(
                    f"/rest/agile/1.0/sprint/{sprint_id}",
                    None,
                    data=payload,
                    error_msg=f"Error ending sprint {sprint_id}"
                )

                # Get the updated sprint data
                return await self.get_sprint_by_id_with_admin_auth(sprint_id)

            except JiraRequestError as e:
                if e.status_code == 404:
                    log.warning(f"Sprint {sprint_id} not found in Jira")
                    return None
                elif attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # exponential backoff
                    log.warning(f"Retrying end_sprint after {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    log.error(f"Failed to end sprint {sprint_id} after {self.retry_attempts} attempts")
                    return None

            except Exception as e:
                log.error(f"Unexpected error ending sprint {sprint_id}: {str(e)}")
                return None

        return None

    async def create_sprint(self, name: str, board_id: int, project_key: str) -> int:
        """Create a new sprint in Jira

        Args:
            name (str): Name of the sprint to create
            board_id (int): ID of the board to create the sprint on
            project_key (str): Key of the project (for logging)

        Returns:
            int: The Jira sprint ID of the created sprint
        """
        log.info(f"Creating new sprint '{name}' on board {board_id} for project {project_key}")

        for attempt in range(self.retry_attempts):
            try:
                # Call Jira API to create the sprint, state is future by default
                payload = {
                    "name": name,
                    "originBoardId": board_id,
                }

                response = await self.client.post(
                    "/rest/agile/1.0/sprint",
                    None,  # Use admin auth
                    data=payload,
                    error_msg=f"Error creating sprint '{name}' for board {board_id}"
                )

                # Return the sprint ID from the response
                sprint_id = response.get("id")
                if not sprint_id:
                    log.error(f"Created sprint response doesn't contain ID: {response}")
                    return None

                log.info(f"Successfully created sprint '{name}' with ID {sprint_id}")
                return sprint_id

            except Exception as e:
                if attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # exponential backoff
                    log.warning(f"Retrying create_sprint after {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    log.error(f"Failed to create sprint '{name}' after {self.retry_attempts} attempts: {str(e)}")
                    raise Exception(f"Failed to create sprint: {str(e)}") from e

        # This shouldn't be reached due to the exception in the last retry
        return None
