from typing import List, Optional
import aiohttp
from aiohttp import ClientTimeout

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.entities.jira import JiraTask
from src.domain.services.jira_service import IJiraService
from src.domain.exceptions.jira_exceptions import (
    JiraConnectionError,
    JiraAuthenticationError,
    JiraRequestError
)


class JiraService(IJiraService):
    def __init__(self):
        self.base_url = settings.JIRA_API_URL.rstrip('/')  # Remove trailing slash if present
        self.auth = aiohttp.BasicAuth(
            settings.JIRA_USERNAME,
            settings.JIRA_API_TOKEN
        )
        self.timeout = ClientTimeout(total=30)  # 30 seconds timeout

    async def get_project_tasks(
        self,
        project_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraTask]:
        jql = f"project = {project_id}"
        if status:
            jql += f" AND status = '{status}'"

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{self.base_url}/rest/api/3/search",
                    params={
                        "jql": jql,
                        "maxResults": limit
                    },
                    auth=self.auth,
                    headers={
                        "Accept": "application/json"
                    }
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
                            id=issue["id"],
                            key=issue["key"],
                            summary=issue["fields"]["summary"],
                            description=issue["fields"].get("description"),
                            status=issue["fields"]["status"]["name"],
                            assignee=issue["fields"].get("assignee", {}).get("displayName"),
                            created_at=issue["fields"]["created"],
                            updated_at=issue["fields"]["updated"],
                            priority=issue["fields"].get("priority", {}).get("name")
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
