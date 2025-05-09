import asyncio
from typing import List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.exceptions.jira_exceptions import JiraRequestError
from src.domain.models.jira.apis.mappers.jira_user import JiraUserMapper
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_user import JiraUserModel
from src.domain.services.jira_user_api_service import IJiraUserAPIService
from src.infrastructure.services.jira_service import JiraAPIClient


class JiraUserAPIService(IJiraUserAPIService):
    """Service to interact with Jira User API"""

    def __init__(
        self,
        client: JiraAPIClient,
        admin_client: Optional[JiraAPIClient] = None
    ):
        self.client = client
        self.admin_client = admin_client
        self.retry_attempts = 3
        self.retry_delay = 1  # seconds

    async def get_user_by_account_id_with_admin_auth(self, account_id: str) -> Optional[JiraUserModel]:
        """Get user by account ID using admin auth"""
        # Sử dụng admin client hoặc client thường với admin auth
        client_to_use = self.admin_client or self.client

        # Gọi API với admin client
        for attempt in range(self.retry_attempts):
            try:
                response_data = await client_to_use.get(
                    session=None,
                    endpoint="/rest/api/3/user",
                    user_id=None,  # Không cần user_id
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

    async def get_user_by_account_id(
        self,
        session: AsyncSession,
        user_id: int,
        account_id: str
    ) -> Optional[JiraUserModel]:
        """Get user details from Jira API by account ID"""
        for attempt in range(self.retry_attempts):
            try:
                response_data = await self.client.get(
                    session=session,
                    endpoint="/rest/api/3/user",
                    user_id=user_id,
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

    async def search_users(
        self,
        session: AsyncSession,
        user_id: int,
        query: str,
        max_results: int = 50
    ) -> List[JiraUserModel]:
        """Search Jira users by query string"""
        try:
            response_data = await self.client.get(
                session=session,
                endpoint="/rest/api/3/user/search",
                user_id=user_id,
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
