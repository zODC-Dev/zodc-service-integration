from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientTimeout

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType, JiraSprintState
from src.domain.constants.refresh_tokens import TokenType
from src.domain.entities.jira import (
    JiraAssignee,
    JiraIssue,
    JiraIssueCreate,
    JiraIssuePriority,
    JiraIssueResponse,
    JiraIssueSprint,
    JiraIssueUpdate,
    JiraProject,
    JiraSprint,
    JiraUser,
)
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError
from src.domain.services.jira_service import IJiraService
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_scheduler_service import ITokenSchedulerService


class JiraService(IJiraService):
    def __init__(
        self,
        redis_service: IRedisService,
        token_scheduler_service: ITokenSchedulerService
    ):
        self.redis_service = redis_service
        self.token_scheduler_service = token_scheduler_service
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

    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssue]:
        token = await self._get_token(user_id)

        # Build JQL query
        jql_conditions = [f"project = {project_key}"]

        # Handle sprint/backlog filter
        if sprint_id:
            jql_conditions.append(f"sprint = {sprint_id}")
        elif is_backlog:
            jql_conditions.append("sprint is EMPTY")

        # Handle issue type filter
        if issue_type:
            jql_conditions.append(f"issuetype = '{issue_type.value}'")

        # Handle search - only using trailing wildcard
        if search:
            # Escape special characters in search term
            escaped_search = search.replace('"', '\\"')
            search_condition = f'(summary ~ "{escaped_search}*" OR description ~ "{escaped_search}*")'
            jql_conditions.append(search_condition)

        jql = " AND ".join(jql_conditions)

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
                            f"Failed to fetch Jira issues: {response_text}"
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
                        JiraIssue(
                            id=issue.get("id", ""),
                            key=issue.get("key", ""),
                            summary=issue.get("fields", {}).get("summary", ""),
                            description=issue.get("fields", {}).get("description"),
                            status=JiraIssueStatus.from_str(
                                issue.get("fields", {}).get("status", {}).get("name", "Unknown")
                            ),
                            assignee=JiraAssignee(
                                user_id=issue.get("fields", {}).get("assignee", {}).get("accountId", ""),
                                email=issue.get("fields", {}).get("assignee", {}).get("emailAddress", ""),
                                avatar_url=issue.get("fields", {}).get(
                                    "assignee", {}).get("avatarUrls", {}).get("48x48", ""),
                                name=issue.get("fields", {}).get("assignee", {}).get("displayName", "")
                            ) if issue.get("fields", {}).get("assignee") else None,
                            priority=JiraIssuePriority(
                                id=issue.get("fields", {}).get("priority", {}).get("id", ""),
                                icon_url=issue.get("fields", {}).get("priority", {}).get("iconUrl", ""),
                                name=issue.get("fields", {}).get("priority", {}).get("name", "")
                            ) if issue.get("fields", {}).get("priority") else None,
                            type=JiraIssueType(issue.get("fields", {}).get("issuetype", {}).get("name", "Task")),
                            sprint=JiraIssueSprint(
                                id=issue.get("fields", {}).get("customfield_10020", [{}])[0].get("id"),
                                name=issue.get("fields", {}).get("customfield_10020", [{}])[0].get("name"),
                                state=JiraSprintState.from_str(
                                    issue.get("fields", {}).get("customfield_10020", [{}])[0].get("state", "Unknown")
                                )
                            ) if issue.get("fields", {}).get("customfield_10020") else None,
                            estimate_point=float(issue.get("fields", {}).get("customfield_10016", 0) or 0),
                            actual_point=float(issue.get("fields", {}).get("customfield_10017")) if issue.get(
                                "fields", {}).get("customfield_10017") else None,
                            created=issue.get("fields", {}).get("created", ""),
                            updated=issue.get("fields", {}).get("updated", "")
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

    async def get_accessible_projects(self, user_id: int) -> List[JiraProject]:
        try:
            token = await self._get_token(user_id)
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{settings.JIRA_BASE_URL}/rest/api/3/project",
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"Bearer {token}"
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
                            url=project.get("self"),
                            avatar_url=project.get("avatarUrls", {}).get("48x48")
                        )
                        for project in data
                    ]

        except aiohttp.ClientConnectorError as e:
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except aiohttp.ClientError as e:
            raise JiraConnectionError(f"Jira API request failed: {str(e)}") from e
        except Exception as e:
            raise JiraRequestError(500, f"Unexpected error: {str(e)}") from e

    async def create_issue(self, user_id: int, issue: JiraIssueCreate) -> JiraIssueResponse:
        """Create a new issue in Jira"""
        token = await self._get_token(user_id)

        # Prepare the request payload
        payload: Dict[str, Any] = {
            "fields": {
                "project": {
                    "key": issue.project_key
                },
                "summary": issue.summary,
                "issuetype": {
                    "name": issue.issue_type
                }
            }
        }

        # Add optional fields if provided
        if issue.description:
            payload["fields"]["description"] = issue.description

        if issue.assignee:
            payload["fields"]["assignee"] = {"accountId": issue.assignee}

        if issue.estimate_points is not None:
            # Assuming story points field is customfield_10002
            # This might need to be adjusted based on your Jira configuration
            payload["fields"]["customfield_10002"] = issue.estimate_points

        # Make the API request
        url = f"{self.base_url}/rest/api/3/issue"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 201:
                    log.error(f"Failed to create Jira issue: {await response.text()}")
                    raise Exception(f"Failed to create Jira issue: {response.status} - {await response.text()}")

                data = await response.json()
                return JiraIssueResponse(
                    issue_id=data["id"],
                    key=data["key"],
                    self_url=data["self"]
                )

    async def get_issue(self, user_id: int, issue_id: str) -> JiraIssue:
        token = await self._get_token(user_id)

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{settings.JIRA_BASE_URL}/rest/api/3/issue/{issue_id}",
                    headers=headers
                ) as response:
                    if response.status != 200:
                        raise JiraRequestError(
                            response.status,
                            "Failed to fetch created issue details"
                        )

                    data = await response.json()
                    return JiraIssue(
                        id=data["id"],
                        key=data["key"],
                        summary=data["fields"]["summary"],
                        description=data["fields"].get("description"),
                        status=JiraIssueStatus.from_str(data["fields"]["status"]["name"]),
                        assignee=JiraAssignee(
                            user_id=data["fields"].get("assignee", {}).get("accountId", ""),
                            email=data["fields"].get("assignee", {}).get("emailAddress", ""),
                            avatar_url=data["fields"].get("assignee", {}).get("avatarUrls", {}).get("48x48", ""),
                            name=data["fields"].get("assignee", {}).get("displayName", "")
                        ) if data["fields"].get("assignee") else None,
                        priority=JiraIssuePriority(
                            id=data["fields"].get("priority", {}).get("id", ""),
                            icon_url=data["fields"].get("priority", {}).get("iconUrl", ""),
                            name=data["fields"].get("priority", {}).get("name", "")
                        ) if data["fields"].get("priority") else None,
                        type=JiraIssueType(data["fields"]["issuetype"]["name"]),
                        sprint=JiraIssueSprint(
                            id=data["fields"].get("sprint", {}).get("id"),
                            name=data["fields"].get("sprint", {}).get("name"),
                            state=JiraSprintState.from_str(data["fields"].get("sprint", {}).get("state", "Unknown"))
                        ) if data["fields"].get("sprint") else None,
                        estimate_point=float(data["fields"].get("customfield_10016", 0) or 0),
                        actual_point=float(data["fields"].get("customfield_10017")
                                           ) if data["fields"].get("customfield_10017") else None,
                        created=data["fields"]["created"],
                        updated=data["fields"]["updated"],
                    )

        except Exception as e:
            raise JiraRequestError(500, f"Failed to fetch issue details: {str(e)}") from e

    async def update_issue(self, user_id: int, issue_id: str, update: JiraIssueUpdate) -> JiraIssueResponse:
        """Update an existing issue in Jira"""
        token = await self._get_token(user_id)

        # Prepare the request payload
        payload: Dict[str, Any] = {
            "fields": {}
        }

        # Add fields that need to be updated
        if update.summary:
            payload["fields"]["summary"] = update.summary

        if update.description:
            payload["fields"]["description"] = update.description

        if update.assignee:
            payload["fields"]["assignee"] = {"accountId": update.assignee}

        if update.estimate_points is not None:
            # Assuming story points field is customfield_10002
            payload["fields"]["customfield_10002"] = update.estimate_points

        if update.actual_points is not None:
            # Assuming actual points field is customfield_10003
            payload["fields"]["customfield_10003"] = update.actual_points

        if update.status:
            # Status updates typically require a transition ID
            # This is a simplified approach - in practice, you might need to
            # get available transitions first and then apply the correct one
            transition_payload = {
                "transition": {
                    "name": update.status
                }
            }

            # Make the transition API request
            transition_url = f"{self.base_url}/rest/api/3/issue/{issue_id}/transitions"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(transition_url, json=transition_payload, headers=headers) as response:
                    if response.status not in (200, 204):
                        log.warning(f"Failed to transition issue status: {await response.text()}")

        # Only make the update request if there are fields to update
        if payload["fields"]:
            url = f"{self.base_url}/rest/api/3/issue/{issue_id}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.put(url, json=payload, headers=headers) as response:
                    if response.status not in (200, 204):
                        log.error(f"Failed to update Jira issue: {await response.text()}")
                        raise Exception(f"Failed to update Jira issue: {response.status} - {await response.text()}")

                    log.info(f"Successfully updated issue {issue_id}")

        return JiraIssueResponse(
            issue_id=issue_id,
            key=issue_id,
            self_url=f"{self.base_url}/rest/api/3/issue/{issue_id}"
        )

    async def get_project_sprints(
        self,
        user_id: int,
        project_id: str,
    ) -> List[JiraSprint]:
        token = await self._get_token(user_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # Try REST API v3 first as it requires fewer permissions
                try:
                    sprints = await self._get_sprints_from_rest_api(session, project_id, headers)
                    if sprints:
                        return sprints
                except JiraRequestError as e:
                    if e.status_code == 401:
                        log.error("Insufficient permissions to access Jira API")
                        raise JiraAuthenticationError("Insufficient Jira permissions") from e
                    log.warning(f"Failed to get sprints via REST API: {str(e)}, trying Agile API")

                # If REST API returned no sprints, try Agile API
                try:
                    async with session.get(
                        f"{settings.JIRA_BASE_URL}/rest/agile/1.0/board",
                        params={"projectKeyOrId": project_id},
                        headers=headers
                    ) as response:
                        response_text = await response.text()

                        if response.status == 401:
                            log.error("Insufficient permissions to access Jira Agile API")
                            # Return empty list if we don't have Agile API access
                            return []

                        if response.status != 200:
                            log.error(f"Failed to fetch project board: {response_text}")
                            raise JiraRequestError(
                                response.status,
                                f"Failed to fetch project board: {response_text}"
                            )

                        boards_data = await response.json()
                        if not boards_data.get("values"):
                            return []

                        board_id = boards_data["values"][0]["id"]

                        # Get sprints for the board
                        async with session.get(
                            f"{settings.JIRA_BASE_URL}/rest/agile/1.0/board/{board_id}/sprint",
                            params={"state": "active,closed,future"},
                            headers=headers
                        ) as sprint_response:
                            sprint_text = await sprint_response.text()

                            if sprint_response.status != 200:
                                log.error(f"Failed to fetch sprints: {sprint_text}")
                                return []

                            sprints_data = await sprint_response.json()
                            return [
                                JiraSprint(
                                    id=sprint["id"],
                                    name=sprint["name"],
                                    state=sprint["state"],
                                    start_date=sprint.get("startDate"),
                                    end_date=sprint.get("endDate"),
                                    goal=sprint.get("goal"),
                                    board_id=board_id
                                )
                                for sprint in sprints_data.get("values", [])
                            ]
                except JiraRequestError as e:
                    if e.status_code == 401:
                        # If we don't have Agile API access, just return what we got from REST API
                        return []
                    raise

        except aiohttp.ClientConnectorError as e:
            log.error(f"Failed to connect to Jira API: {str(e)}")
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except JiraAuthenticationError:
            raise
        except Exception as e:
            log.error(f"Unexpected error during sprint fetch: {str(e)}")
            raise JiraRequestError(500, f"Failed to fetch sprints: {str(e)}") from e

    async def _get_sprints_from_rest_api(
        self,
        session: aiohttp.ClientSession,
        project_id: str,
        headers: Dict[str, str]
    ) -> List[JiraSprint]:
        """Get sprints using REST API v3"""
        try:
            # Use JQL to get all issues with sprint information
            jql = f"project = {project_id} AND sprint is not EMPTY ORDER BY sprint ASC"
            async with session.get(
                f"{settings.JIRA_BASE_URL}/rest/api/3/search",
                params={
                    "jql": jql,
                    "fields": "sprint",
                    "maxResults": 100
                },
                headers=headers
            ) as response:
                response_text = await response.text()

                if response.status == 401:
                    raise JiraRequestError(401, "Unauthorized access to Jira API")

                if response.status != 200:
                    log.error(f"Failed to fetch sprints via REST API: {response_text}")
                    raise JiraRequestError(
                        response.status,
                        f"Failed to fetch sprints via REST API: {response_text}"
                    )

                data = await response.json()

                # Extract unique sprints from issues
                sprints_dict = {}
                for issue in data.get("issues", []):
                    for sprint in issue.get("fields", {}).get("sprint", []):
                        if sprint["id"] not in sprints_dict:
                            sprints_dict[sprint["id"]] = JiraSprint(
                                id=sprint["id"],
                                name=sprint["name"],
                                state=JiraSprintState.from_str(sprint["state"].lower())
                            )

                return list(sprints_dict.values())

        except Exception as e:
            log.error(f"Failed to fetch sprints via REST API: {str(e)}")
            raise JiraRequestError(500, f"Failed to fetch sprints via REST API: {str(e)}") from e

    async def get_project_users(
        self,
        user_id: int,
        project_key: str
    ) -> List[JiraUser]:
        """Get users for a Jira project"""
        token = await self._get_token(user_id)

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{settings.JIRA_BASE_URL}/rest/api/3/user/assignable/search",
                    params={
                        "project": project_key,
                        "maxResults": 1000  # Get maximum number of users
                    },
                    headers=headers
                ) as response:
                    if response.status != 200:
                        raise JiraRequestError(
                            response.status,
                            "Failed to fetch project users"
                        )

                    users_data = await response.json()
                    return [
                        JiraUser(
                            display_name=user.get("displayName", ""),
                            account_id=user.get("accountId", ""),
                            email_address=user.get("emailAddress", "")
                        )
                        for user in users_data
                        # Filter out system and app accounts
                        if not (
                            user.get("accountType") == "app" or
                            user.get("accountId", "").startswith("557058:") or
                            "addon" in user.get("accountType", "").lower()
                        )
                    ]

        except aiohttp.ClientConnectorError as e:
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except Exception as e:
            raise JiraRequestError(500, f"Failed to fetch project users: {str(e)}") from e
