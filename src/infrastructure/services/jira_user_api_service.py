import asyncio
from typing import List, Optional

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.exceptions.jira_exceptions import JiraRequestError
from src.domain.models.jira.apis.mappers.jira_user import JiraUserMapper
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_user import JiraUserModel
from src.domain.services.jira_user_api_service import IJiraUserAPIService
from src.infrastructure.services.jira_service import JiraAPIClient


class JiraUserAPIService(IJiraUserAPIService):
    """Service to interact with Jira User API"""

    def __init__(self, client: JiraAPIClient):
        self.client = client
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds
        self.system_user_id = settings.JIRA_SYSTEM_USER_ID

    async def get_user_by_account_id_with_system_user(self, account_id: str) -> Optional[JiraUserModel]:
        """Get user by account ID using system user"""
        return await self.get_user_by_account_id(self.system_user_id, account_id)

    async def get_user_by_account_id(self, user_id: int, account_id: str) -> Optional[JiraUserModel]:
        """Get user details from Jira API by account ID"""
        for attempt in range(self.retry_attempts):
            try:
                response_data = await self.client.get(
                    "/rest/api/3/user",
                    user_id,
                    params={"accountId": account_id},
                    error_msg=f"Error fetching user with account ID {account_id}"
                )

                log.info(f"Response data when get user: {response_data}")

                # Map response to domain model
                user: JiraUserModel = await self.client.map_to_domain(
                    response_data,
                    JiraUserAPIGetResponseDTO,
                    JiraUserMapper
                )

                return user

            except JiraRequestError as e:
                if e.status_code == 404:
                    log.warning(f"User with account ID {account_id} not found in Jira")
                    return None
                elif attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # exponential backoff
                    log.warning(f"Retrying get_user_by_account_id after {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    log.error(f"Failed to fetch user with account ID {account_id} after {self.retry_attempts} attempts")
                    return None

            except Exception as e:
                log.error(f"Unexpected error fetching user with account ID {account_id}: {str(e)}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    return None

        return None

    async def search_users(self, user_id: int, query: str, max_results: int = 50) -> List[JiraUserModel]:
        """Search Jira users by query string"""
        try:
            response_data = await self.client.get(
                "/rest/api/3/user/search",
                user_id,
                params={"query": query, "maxResults": max_results},
                error_msg=f"Error searching users with query '{query}'"
            )

            users: List[JiraUserModel] = []
            for user_data in response_data:
                user: JiraUserModel = await self.client.map_to_domain(
                    user_data,
                    JiraUserAPIGetResponseDTO,
                    JiraUserMapper
                )
                users.append(user)

            return users
        except Exception as e:
            log.error(f"Error searching users: {str(e)}")
            return []
