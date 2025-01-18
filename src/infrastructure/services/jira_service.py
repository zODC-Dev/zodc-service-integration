from typing import List, Optional

import aiohttp
from aiohttp import ClientTimeout

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.entities.jira import JiraIssueCreate, JiraProject, JiraTask
from src.domain.entities.jira_api import (
    JiraADFContent,
    JiraADFDocument,
    JiraADFParagraph,
    JiraCreateIssueFields,
    JiraCreateIssueRequest,
    JiraCreateIssueResponse,
    JiraIssueTypeReference,
    JiraPriorityReference,
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
                priority=JiraPriorityReference(name=issue.priority) if issue.priority else None,
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

                    log.info(f"Response data: {response_data}")
                    # Parse the create response
                    create_response = JiraCreateIssueResponse.model_validate(response_data)

                    # Get the full issue details
                    return create_response

        except aiohttp.ClientConnectorError as e:
            raise JiraConnectionError(f"Could not connect to Jira API: {str(e)}") from e
        except Exception as e:
            log.error(f"Error creating issue: {str(e)}")
            raise JiraRequestError(500, f"Unexpected error: {str(e)}") from e

    async def get_issue(self, user_id: int, issue_id: str) -> JiraTask:
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
                    return JiraTask(
                        id=data["id"],
                        key=data["key"],
                        summary=data["fields"]["summary"],
                        description=data["fields"].get("description"),
                        status=data["fields"]["status"]["name"],
                        assignee=data["fields"].get("assignee", {}).get("displayName"),
                        created_at=data["fields"]["created"],
                        updated_at=data["fields"]["updated"],
                        priority=data["fields"].get("priority", {}).get("name")
                    )

        except Exception as e:
            raise JiraRequestError(500, f"Failed to fetch issue details: {str(e)}") from e
