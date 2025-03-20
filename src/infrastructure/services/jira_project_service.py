from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientTimeout

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.jira import JiraIssueType
from src.domain.constants.refresh_tokens import TokenType
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_project import JiraProjectModel, JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.jira_project_service import IJiraProjectService
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_scheduler_service import ITokenSchedulerService
from src.infrastructure.dtos.jira.issue_responses import JiraAPIIssueResponse
from src.infrastructure.dtos.jira.project_responses import (
    JiraAPIProjectResponse,
    JiraAPIProjectSprintResponse,
    JiraAPIProjectUserResponse,
)
from src.infrastructure.mappers.jira_issue_mapper import JiraIssueMapper
from src.infrastructure.mappers.jira_project_mapper import JiraProjectMapper


class JiraProjectService(IJiraProjectService):
    def __init__(
        self,
        redis_service: IRedisService,
        token_scheduler_service: ITokenSchedulerService,
        user_repository: IJiraUserRepository
    ):
        self.redis_service = redis_service
        self.token_scheduler_service = token_scheduler_service
        self.user_repository = user_repository
        self.timeout = ClientTimeout(total=30)
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
        limit: int = 50
    ) -> List[JiraIssueModel]:
        token = await self._get_token(user_id)
        try:
            # Build JQL query
            jql_parts = [f"project = {project_key}"]
            if sprint_id:
                jql_parts.append(f"sprint = {sprint_id}")
            elif is_backlog is not None:
                jql_parts.append("sprint is EMPTY" if is_backlog else "sprint is not EMPTY")
            if issue_type:
                jql_parts.append(f"issuetype = {issue_type.value}")
            if search:
                jql_parts.append(f"(summary ~ '{search}' OR description ~ '{search}')")

            jql = " AND ".join(jql_parts)

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{settings.JIRA_BASE_URL}/rest/api/3/search",
                    headers=self._get_headers(token),
                    params={
                        "jql": jql,
                        "maxResults": limit,
                        "fields": "summary,description,status,assignee,priority,issuetype,customfield_10016,customfield_10017,customfield_10020,created,updated"
                    }
                ) as response:
                    if response.status == 401:
                        raise JiraAuthenticationError("Invalid or expired token")
                    if response.status != 200:
                        raise JiraRequestError(response.status, "Failed to fetch issues")

                    data = await response.json()
                    issues = []
                    for issue_data in data.get("issues", []):
                        api_response = JiraAPIIssueResponse.model_validate(issue_data)
                        issue = JiraIssueMapper.to_domain_issue(api_response)
                        issues.append(issue)
                    return issues

        except aiohttp.ClientConnectorError as e:
            log.error(f"Failed to connect to Jira API: {str(e)}")
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e

    async def get_project_sprints(
        self,
        user_id: int,
        project_id: str
    ) -> List[JiraSprintModel]:
        """Get all sprints in a project"""
        token = await self._get_token(user_id)

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Get board ID first
                board_data = await self._get_project_board(session, token, project_id)
                if not board_data:
                    return []

                board_id = board_data[0]["id"]

                # Get sprints for the board
                async with session.get(
                    f"{self.base_url}/rest/agile/1.0/board/{board_id}/sprint",
                    params={"state": "active,closed,future"},
                    headers=self._get_headers(token)
                ) as response:
                    if response.status != 200:
                        raise JiraRequestError(
                            response.status,
                            await response.text()
                        )

                    data = await response.json()
                    sprints = [
                        JiraAPIProjectSprintResponse.model_validate(sprint)
                        for sprint in data.get("values", [])
                    ]
                    return [
                        JiraProjectMapper.to_domain_sprint(sprint)
                        for sprint in sprints
                    ]

        except Exception as e:
            log.error(f"Error fetching project sprints: {str(e)}")
            raise JiraRequestError(500, str(e)) from e

    async def get_project_users(
        self,
        user_id: int,
        project_key: str
    ) -> List[JiraUserModel]:
        """Get all users in a project"""
        token = await self._get_token(user_id)

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/rest/api/3/user/assignable/search",
                    params={
                        "project": project_key,
                        "maxResults": 1000
                    },
                    headers=self._get_headers(token)
                ) as response:
                    if response.status != 200:
                        raise JiraRequestError(
                            response.status,
                            await response.text()
                        )

                    data = await response.json()
                    users = [
                        JiraAPIProjectUserResponse.model_validate(user)
                        for user in data
                        if not (
                            user.get("accountType") == "app" or
                            user.get("accountId", "").startswith("557058:") or
                            "addon" in user.get("accountType", "").lower()
                        )
                    ]
                    return [
                        JiraProjectMapper.to_domain_user(user)
                        for user in users
                    ]

        except Exception as e:
            log.error(f"Error fetching project users: {str(e)}")
            raise JiraRequestError(500, str(e)) from e

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

            data: Dict[str, Any] = await response.json()
            return data.get("values", [])
