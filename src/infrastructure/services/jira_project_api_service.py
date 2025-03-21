from typing import Any, Dict, List, Optional

import aiohttp

from src.app.mappers.jira_mapper import JiraSprintMapper, JiraUserMapper
from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.jira import JiraIssueType
from src.domain.constants.refresh_tokens import TokenType
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_project import JiraProjectModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_scheduler_service import ITokenSchedulerService
from src.infrastructure.dtos.jira.issue_responses import JiraAPIIssueResponse
from src.infrastructure.dtos.jira.project_responses import JiraAPIProjectResponse
from src.infrastructure.dtos.jira.sprint_responses import JiraAPISprintResponse
from src.infrastructure.dtos.jira.user_responses import JiraAPIUserResponse
from src.infrastructure.mappers.jira_issue_mapper import JiraIssueMapper
from src.infrastructure.mappers.jira_project_mapper import JiraProjectMapper


class JiraProjectAPIService(IJiraProjectAPIService):
    def __init__(
        self,
        redis_service: IRedisService,
        token_scheduler_service: ITokenSchedulerService,
        user_repository: IJiraUserRepository,
        timeout: int = 30
    ):
        self.redis_service = redis_service
        self.token_scheduler_service = token_scheduler_service
        self.user_repository = user_repository
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.base_url = settings.JIRA_BASE_URL

    async def _get_token(self, user_id: int) -> str:
        # Schedule token refresh check
        await self.token_scheduler_service.schedule_token_refresh(user_id)

        # Try to get token from cache first
        token = await self.redis_service.get_cached_jira_token(user_id)
        if token:
            return token

        # If not in cache, using refresh token to get new access token
        await self.token_scheduler_service.refresh_token_chain(user_id, TokenType.JIRA)

        # Try to get token from cache again
        token = await self.redis_service.get_cached_jira_token(user_id)
        if token:
            return token

        raise JiraAuthenticationError("Failed to get Jira token")

    async def get_project_details(self, user_id: int, project_key: str) -> JiraProjectModel:
        """Get project details from Jira API"""
        try:
            token = await self._get_token(user_id)
            log.info(f"Got token for user {user_id}: {token}...")  # Log first 10 chars of token

            headers = self._get_headers(token)
            url = f"{settings.JIRA_BASE_URL}/rest/api/3/project/{project_key}"

            log.info(f"Fetching project details from: {url}")
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 401:
                        log.error(f"Authentication failed for user {user_id}")
                        raise JiraAuthenticationError("Invalid or expired token")
                    if response.status != 200:
                        error_text = await response.text()
                        log.error(f"Failed to fetch project details. Status: {response.status}, Error: {error_text}")
                        raise JiraRequestError(response.status, f"Failed to fetch project details: {error_text}")

                    data = await response.json()

                    api_response = JiraAPIProjectResponse.model_validate(data)
                    return JiraProjectMapper.to_domain(api_response)

        except aiohttp.ClientConnectorError as e:
            log.error(f"Failed to connect to Jira API: {str(e)}")
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except Exception as e:
            log.error(f"Error fetching project details: {str(e)}", exc_info=True)
            raise

    async def get_project_users(self, user_id: int, project_key: str) -> List[JiraUserModel]:
        """Get project users from Jira API"""
        try:
            token = await self._get_token(user_id)

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{settings.JIRA_BASE_URL}/rest/api/3/user/assignable/search",
                    params={"project": project_key},
                    headers=self._get_headers(token)
                ) as response:
                    if response.status == 401:
                        raise JiraAuthenticationError("Invalid or expired token")
                    if response.status != 200:
                        raise JiraRequestError(response.status, "Failed to fetch project users")

                    data = await response.json()
                    users = []
                    for user_data in data:
                        api_response = JiraAPIUserResponse.model_validate(user_data)
                        users.append(JiraUserMapper.to_domain(api_response))
                    return users

        except aiohttp.ClientConnectorError as e:
            log.error(f"Failed to connect to Jira API: {str(e)}")
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except Exception as e:
            log.error(f"Error fetching project users: {str(e)}")
            raise

    async def get_project_sprints(self, user_id: int, project_key: str) -> List[JiraSprintModel]:
        """Get project sprints from Jira API"""
        try:
            token = await self._get_token(user_id)

            # First get the board ID for the project
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{settings.JIRA_BASE_URL}/rest/agile/1.0/board",
                    params={"projectKeyOrId": project_key},
                    headers=self._get_headers(token)
                ) as response:
                    if response.status == 401:
                        raise JiraAuthenticationError("Invalid or expired token")
                    if response.status != 200:
                        raise JiraRequestError(response.status, "Failed to fetch project board")

                    data = await response.json()
                    if not data.get("values"):
                        return []

                    board_id = data["values"][0]["id"]

                    # Then get sprints for the board
                    async with session.get(
                        f"{settings.JIRA_BASE_URL}/rest/agile/1.0/board/{board_id}/sprint",
                        headers=self._get_headers(token)
                    ) as sprint_response:
                        if sprint_response.status == 401:
                            raise JiraAuthenticationError("Invalid or expired token")
                        if sprint_response.status != 200:
                            raise JiraRequestError(sprint_response.status, "Failed to fetch sprints")

                        sprint_data = await sprint_response.json()
                        sprints = []
                        for sprint in sprint_data.get("values", []):
                            api_response = JiraAPISprintResponse.model_validate(sprint)
                            sprints.append(JiraSprintMapper.to_domain(api_response))
                        return sprints

        except aiohttp.ClientConnectorError as e:
            log.error(f"Failed to connect to Jira API: {str(e)}")
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except Exception as e:
            log.error(f"Error fetching project sprints: {str(e)}")
            raise

    async def get_accessible_projects(self, user_id: int) -> List[JiraProjectModel]:
        """Get all accessible Jira projects for a user"""
        token = await self._get_token(user_id)

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/rest/api/3/project",
                    headers=self._get_headers(token)
                ) as response:
                    if response.status != 200:
                        raise JiraRequestError(
                            response.status,
                            await response.text()
                        )

                    data = await response.json()
                    projects = [
                        JiraAPIProjectResponse.model_validate(project)
                        for project in data
                    ]
                    return [
                        JiraProjectMapper.to_domain_project(project)
                        for project in projects
                    ]

        except aiohttp.ClientConnectorError as e:
            log.error(f"Failed to connect to Jira API: {str(e)}")
            raise JiraConnectionError(str(e)) from e
        except Exception as e:
            log.error(f"Error fetching Jira projects: {str(e)}")
            raise JiraRequestError(500, str(e)) from e

    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50,
        start_at: int = 0
    ) -> List[JiraIssueModel]:
        """Get project issues from Jira API with pagination"""
        try:
            token = await self._get_token(user_id)

            # Build JQL query
            jql_parts = [f"project = {project_key}"]
            if sprint_id:
                jql_parts.append(f"sprint = {sprint_id}")
            if is_backlog is not None:
                jql_parts.append("sprint is EMPTY" if is_backlog else "sprint is not EMPTY")
            if issue_type:
                jql_parts.append(f"issuetype = {issue_type.value}")
            if search:
                jql_parts.append(f"(summary ~ \"{search}\" OR description ~ \"{search}\")")

            jql = " AND ".join(jql_parts)

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                url = f"{settings.JIRA_BASE_URL}/rest/api/3/search"
                params = {
                    "jql": jql,
                    "maxResults": limit,
                    "startAt": start_at,
                    "fields": "summary,description,status,assignee,priority,issuetype,created,updated,customfield_10016,customfield_10017,customfield_10020"
                }

                async with session.get(
                    url,
                    params=params,
                    headers=self._get_headers(token)
                ) as response:
                    if response.status == 401:
                        raise JiraAuthenticationError("Invalid or expired token")
                    if response.status != 200:
                        raise JiraRequestError(response.status, "Failed to fetch project issues")

                    data = await response.json()
                    issues = []
                    for issue_data in data.get("issues", []):
                        api_response = JiraAPIIssueResponse.model_validate(issue_data)
                        issues.append(JiraIssueMapper.to_domain_issue(api_response))
                    return issues

        except aiohttp.ClientConnectorError as e:
            log.error(f"Failed to connect to Jira API: {str(e)}")
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except Exception as e:
            log.error(f"Error fetching project issues: {str(e)}")
            raise

    def _get_headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

    async def _get_project_board(
        self,
        session: aiohttp.ClientSession,
        token: str,
        project_id: str
    ) -> List[Dict[str, Any]]:
        async with session.get(
            f"{self.base_url}/rest/agile/1.0/board",
            params={"projectKeyOrId": project_id},
            headers=self._get_headers(token)
        ) as response:
            if response.status != 200:
                raise JiraRequestError(
                    response.status,
                    await response.text()
                )

            data: Dict[str, List[Dict[str, Any]]] = await response.json()
            return data.get("values", [])
