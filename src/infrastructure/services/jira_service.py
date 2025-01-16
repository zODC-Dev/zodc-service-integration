from typing import List, Optional
import aiohttp
from aiohttp import ClientTimeout

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.entities.jira import JiraTask, JiraProject
from src.domain.services.jira_service import IJiraService
from src.domain.exceptions.jira_exceptions import (
    JiraConnectionError,
    JiraAuthenticationError,
    JiraRequestError
)
from src.infrastructure.services.redis_service import RedisService


class JiraService(IJiraService):
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.timeout = ClientTimeout(total=30)

    async def _get_token(self, user_id: int) -> str:
        # Try to get token from cache first
        token = await self.redis_service.get_cached_jira_token(user_id)
        log.info(f"Token: {token}")
        if token:
            log.info(f"Token from cache: {token}")
            return token

        # If not in cache, request new token from auth service
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                f"http://localhost:8000/api/v1/internal/jira/token/{user_id}",
            ) as response:
                if response.status != 200:
                    raise JiraAuthenticationError("Failed to obtain Jira token")

                data = await response.json()
                log.info(f"Data: {data}")
                token = data.get("access_token")
                log.info(f"Token: {token}")
                # Cache the token
                await self.redis_service.cache_jira_token(user_id, token)
                return token

    async def get_project_tasks(
        self,
        user_id: int,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraTask]:
        token = await self._get_token(user_id)
        jql = f"project = {project_id}"
        if status:
            jql += f" AND status = '{status}'"

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{settings.JIRA_BASE_URL}/rest/api/3/search",
                    params={
                        "jql": jql,
                        "maxResults": limit
                    },
                    headers=headers
                ) as response:
                    response_text = await response.text()
                    log.info(f"Response text: {response_text}")

                    if response.status == 401:
                        log.error("Jira authentication failed")
                        raise JiraAuthenticationError("Invalid Jira credentials")

                    if response.status == 403:
                        log.error("Insufficient permissions to access Jira API")
                        raise JiraAuthenticationError("Insufficient Jira permissions")

                    if response.status != 200:
                        log.error(f"Jira API request failed: {response_text}")
                        raise JiraRequestError(
                            response.status,
                            f"Failed to fetch Jira tasks: {response_text}"
                        )

                    try:
                        data = await response.json()
                    except ValueError as e:
                        log.error(f"Failed to parse Jira API response: {response_text}")
                        raise JiraRequestError(
                            500,
                            f"Invalid JSON response from Jira API: {str(e)}"
                        ) from e

                    return [
                        JiraTask(
                            id=issue.get("id", ""),
                            key=issue.get("key", ""),
                            summary=issue.get("fields", {}).get("summary", ""),
                            description=issue.get("fields", {}).get("description"),
                            status=issue.get("fields", {}).get("status", {}).get("name", "Unknown"),
                            assignee=issue.get("fields", {}).get("assignee", {}).get(
                                "displayName") if issue.get("fields", {}).get("assignee") else None,
                            created_at=issue.get("fields", {}).get("created", ""),
                            updated_at=issue.get("fields", {}).get("updated", ""),
                            priority=issue.get("fields", {}).get("priority", {}).get(
                                "name") if issue.get("fields", {}).get("priority") else None
                        )
                        for issue in data.get("issues", [])
                    ]

        except aiohttp.ClientConnectorError as e:
            log.error(f"Failed to connect to Jira API: {str(e)}")
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e

        except aiohttp.ClientError as e:
            log.error(f"Jira API request failed: {str(e)}")
            raise JiraConnectionError(f"Jira API request failed: {str(e)}") from e

        except Exception as e:
            log.error(f"Unexpected error during Jira API request: {str(e)}")
            raise JiraRequestError(500, f"Unexpected error: {str(e)}") from e

    async def get_accessible_projects(self) -> List[JiraProject]:
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{settings.JIRA_BASE_URL}/rest/api/3/project",
                    headers={
                        "Accept": "application/json"
                    }
                ) as response:
                    response_text = await response.text()

                    if response.status == 401:
                        raise JiraAuthenticationError("Invalid Jira credentials")

                    if response.status == 403:
                        raise JiraAuthenticationError("Insufficient Jira permissions")

                    if response.status != 200:
                        raise JiraRequestError(
                            response.status,
                            f"Failed to fetch Jira projects: {response_text}"
                        )

                    try:
                        data = await response.json()
                    except ValueError as e:
                        raise JiraRequestError(
                            500,
                            f"Invalid JSON response from Jira API: {str(e)}"
                        ) from e

                    return [
                        JiraProject(
                            id=project["id"],
                            key=project["key"],
                            name=project["name"],
                            description=project.get("description"),
                            project_type=project.get("projectTypeKey"),
                            project_category=project.get("projectCategory", {}).get("name"),
                            lead=project.get("lead", {}).get("displayName"),
                            url=project.get("self")
                        )
                        for project in data
                    ]

        except aiohttp.ClientConnectorError as e:
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except aiohttp.ClientError as e:
            raise JiraConnectionError(f"Jira API request failed: {str(e)}") from e
        except Exception as e:
            raise JiraRequestError(500, f"Unexpected error: {str(e)}") from e
