from typing import Any, Dict, List, Optional

import aiohttp
from aiohttp import ClientTimeout

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.jira import JiraIssueType, JiraIssueStatus, JiraSprintState
from src.domain.entities.jira import JiraIssueCreate, JiraProject, JiraIssue, JiraIssueUpdate, JiraSprint, JiraAssignee, JiraIssuePriority, JiraIssueSprint
from src.domain.entities.jira_api import (
    JiraADFContent,
    JiraADFDocument,
    JiraADFParagraph,
    JiraCreateIssueFields,
    JiraCreateIssueRequest,
    JiraCreateIssueResponse,
    JiraIssueTypeReference,
    JiraIssuePriorityReference,
    JiraProjectReference,
    JiraUserReference,
)
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraConnectionError, JiraRequestError
from src.domain.services.jira_service import IJiraService
from src.infrastructure.services.redis_service import RedisService


class JiraService(IJiraService):
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.timeout = ClientTimeout(total=30)

    async def _get_token(self, user_id: int) -> str:
        # Try to get token from cache first
        token = await self.redis_service.get_cached_jira_token(user_id)
        if token:
            return token

        # If not in cache, request new token from auth service
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/internal/jira/token/{user_id}",
            ) as response:
                if response.status != 200:
                    raise JiraAuthenticationError("Failed to obtain Jira token")

                data = await response.json()
                token = data.get("access_token")
                # Cache the token
                await self.redis_service.cache_jira_token(user_id, token)
                return token

    async def get_project_issues(
        self,
        user_id: int,
        project_id: str,
        sprint: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        limit: int = 50
    ) -> List[JiraIssue]:
        token = await self._get_token(user_id)

        # Build JQL query
        jql_conditions = [f"project = {project_id}"]

        # Handle sprint/backlog filter
        if sprint:
            jql_conditions.append(f"sprint = {sprint}")
        elif is_backlog:
            jql_conditions.append("sprint is EMPTY")

        # Handle issue type filter
        if issue_type:
            jql_conditions.append(f"issuetype = '{issue_type.value}'")

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
                                account_id=issue.get("fields", {}).get("assignee", {}).get("accountId", ""),
                                email_address=issue.get("fields", {}).get("assignee", {}).get("emailAddress", ""),
                                avatar_urls=issue.get("fields", {}).get(
                                    "assignee", {}).get("avatarUrls", {}).get("24x24", ""),
                                display_name=issue.get("fields", {}).get("assignee", {}).get("displayName", "")
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

    async def create_issue(self, user_id: int, issue: JiraIssueCreate) -> JiraCreateIssueResponse:
        token = await self._get_token(user_id)

        # Create type-safe request using Pydantic models
        issue_request = JiraCreateIssueRequest(
            fields=JiraCreateIssueFields(
                project=JiraProjectReference(
                    key=issue.project_key
                ),
                summary=issue.summary,
                issuetype=JiraIssueTypeReference(
                    name=issue.issue_type.value
                ),
                description=JiraADFDocument(
                    content=[
                        JiraADFParagraph(
                            content=[
                                JiraADFContent(
                                    text=issue.description or ""
                                )
                            ]
                        )
                    ]
                ),
                priority=JiraIssuePriorityReference(name=issue.priority) if issue.priority else None,
                assignee=JiraUserReference(id=issue.assignee) if issue.assignee else None,
                labels=issue.labels
            )
        )

        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{settings.JIRA_BASE_URL}/rest/api/3/issue",
                    json=issue_request.model_dump(exclude_none=True),
                    headers=headers
                ) as response:
                    response_data = await response.json()

                    if response.status != 201:
                        raise JiraRequestError(
                            response.status,
                            f"Failed to create Jira issue: {response_data}"
                        )

                    # Parse the create response
                    create_response = JiraCreateIssueResponse.model_validate(response_data)

                    # Get the full issue details
                    return create_response

        except aiohttp.ClientConnectorError as e:
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except Exception as e:
            log.error(f"Error creating issue: {str(e)}")
            raise JiraRequestError(500, f"Unexpected error: {str(e)}") from e

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
                        state=data["fields"]["status"]["name"],
                        assignee=JiraAssignee(
                            account_id=data["fields"].get("assignee", {}).get("accountId", ""),
                            email_address=data["fields"].get("assignee", {}).get("emailAddress", ""),
                            avatar_urls=data["fields"].get("assignee", {}).get("avatarUrls", {}).get("48x48", ""),
                            display_name=data["fields"].get("assignee", {}).get("displayName", "")
                        ) if data["fields"].get("assignee") else None,
                        priority=JiraIssuePriority(
                            id=data["fields"].get("priority", {}).get("id", ""),
                            icon_url=data["fields"].get("priority", {}).get("iconUrl", ""),
                            name=data["fields"].get("priority", {}).get("name", "")
                        ) if data["fields"].get("priority") else None,
                        type=JiraIssueType(data["fields"]["issuetype"]["name"]),
                        sprint=JiraIssueSprint(
                            id=data["fields"].get("sprint", {}).get("id"),
                            name=data["fields"].get("sprint", {}).get("name")
                        ) if data["fields"].get("sprint") else None,
                        estimate_point=float(data["fields"].get("customfield_10016", 0) or 0),
                        actual_point=float(data["fields"].get("customfield_10017")
                                           ) if data["fields"].get("customfield_10017") else None,
                        created=data["fields"]["created"],
                        updated=data["fields"]["updated"]
                    )

        except Exception as e:
            raise JiraRequestError(500, f"Failed to fetch issue details: {str(e)}") from e

    async def update_issue(
        self,
        user_id: int,
        issue_id: str,
        update: JiraIssueUpdate
    ) -> JiraIssue:
        token = await self._get_token(user_id)

        try:
            # Prepare update fields
            update_fields: Dict[str, Any] = {}

            if update.assignee is not None:
                update_fields["assignee"] = {"id": update.assignee} if update.assignee else None

            if update.status is not None:
                # First, get available transitions
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.get(
                        f"{settings.JIRA_BASE_URL}/rest/api/3/issue/{issue_id}/transitions",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/json"
                        }
                    ) as response:
                        if response.status != 200:
                            raise JiraRequestError(
                                response.status,
                                "Failed to get issue transitions"
                            )
                        transitions = await response.json()

                        # Find the transition ID for the desired status
                        transition_id = None
                        for transition in transitions["transitions"]:
                            if transition["to"]["name"].lower() == update.status.value.lower():
                                transition_id = transition["id"]
                                break

                        if transition_id:
                            # Perform the transition
                            await session.post(
                                f"{settings.JIRA_BASE_URL}/rest/api/3/issue/{issue_id}/transitions",
                                headers={
                                    "Authorization": f"Bearer {token}",
                                    "Accept": "application/json",
                                    "Content-Type": "application/json"
                                },
                                json={
                                    "transition": {"id": transition_id}
                                }
                            )

            if update.estimate_points is not None:
                update_fields["customfield_10016"] = update.estimate_points

            if update.actual_points is not None:
                update_fields["customfield_10017"] = update.actual_points

            # Update the issue if there are fields to update
            if update_fields:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    await session.put(
                        f"{settings.JIRA_BASE_URL}/rest/api/3/issue/{issue_id}",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Accept": "application/json",
                            "Content-Type": "application/json"
                        },
                        json={"fields": update_fields}
                    )

            # Get and return the updated issue
            return await self.get_issue(user_id, issue_id)

        except aiohttp.ClientConnectorError as e:
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except Exception as e:
            raise JiraRequestError(500, f"Failed to update issue: {str(e)}") from e

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
                                state=sprint["state"].lower(),  # Normalize state to match Agile API
                                start_date=sprint.get("startDate"),
                                end_date=sprint.get("endDate"),
                                goal=sprint.get("goal", None),
                                board_id=sprint.get("originBoardId", 0)
                            )

                return list(sprints_dict.values())

        except Exception as e:
            log.error(f"Failed to fetch sprints via REST API: {str(e)}")
            raise JiraRequestError(500, f"Failed to fetch sprints via REST API: {str(e)}")
