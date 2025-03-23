from typing import Any, Dict, List, Optional

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus
from src.domain.models.jira_issue import JiraIssueCreateDTO, JiraIssueModel, JiraIssueUpdateDTO
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.infrastructure.dtos.jira.issue_responses import JiraAPIIssueResponse
from src.infrastructure.mappers.jira_issue_mapper import JiraIssueMapper
from src.infrastructure.services.jira_service import JiraAPIClient


class JiraIssueAPIService(IJiraIssueAPIService):
    """Service to interact with Jira Issue API"""

    def __init__(self, jira_api_client: JiraAPIClient):
        self.client = jira_api_client

    async def get_issue(self, user_id: int, issue_id: str) -> JiraIssueModel:
        """Get issue information from Jira API"""
        response_data = await self.client.get(
            f"/rest/api/3/issue/{issue_id}",
            user_id,
            params={"fields": "summary,description,status,assignee,priority,issuetype,created,updated,customfield_10016,customfield_10017,customfield_10020"},
            error_msg=f"Error when getting issue {issue_id}"
        )

        return await self.client.map_to_domain(
            response_data,
            JiraAPIIssueResponse,
            JiraIssueMapper
        )

    async def create_issue(self, user_id: int, issue: JiraIssueCreateDTO) -> JiraIssueModel:
        """Create new issue in Jira"""
        # Prepare payload
        payload = {
            "fields": {
                "project": {"key": issue.project_key},
                "summary": issue.summary,
                "description": issue.description,
                "issuetype": {"name": issue.type.value},
            }
        }

        # Add optional fields
        if issue.assignee:
            payload["fields"]["assignee"] = {"accountId": issue.assignee}

        if issue.estimate_point is not None:
            payload["fields"]["customfield_10016"] = issue.estimate_point

        response_data = await self.client.post(
            "/rest/api/3/issue",
            user_id,
            payload,
            error_msg="Error when creating issue"
        )

        # Get new created issue
        created_issue_id = response_data.get("id")
        return await self.get_issue(user_id, created_issue_id)

    async def update_issue(self, user_id: int, issue_id: str, update: JiraIssueUpdateDTO) -> JiraIssueModel:
        """Update issue in Jira"""
        # Prepare payload for fields
        payload = {"fields": {}}

        if update.summary is not None:
            payload["fields"]["summary"] = update.summary

        if update.description is not None:
            payload["fields"]["description"] = self._text_to_adf(update.description)

        if update.assignee_id is not None:
            payload["fields"]["assignee"] = {"accountId": update.assignee_id}

        if update.estimate_point is not None:
            payload["fields"]["customfield_10016"] = update.estimate_point

        if update.actual_point is not None:
            payload["fields"]["customfield_10017"] = update.actual_point

        log.info(f"Updating issue {issue_id} with payload: {payload}")

        # Only send request if there is a field to update
        if payload["fields"]:
            await self.client.put(
                f"/rest/api/3/issue/{issue_id}",
                user_id,
                payload,
                error_msg=f"Error when updating issue {issue_id}"
            )

        # Update status if there is one
        if update.status is not None:
            await self.transition_issue(user_id, issue_id, update.status)

        # Return issue after update
        return await self.get_issue(user_id, issue_id)

    async def search_issues(
        self,
        user_id: int,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: Optional[List[str]] = None
    ) -> List[JiraIssueModel]:
        """Search issues by JQL"""
        if fields is None:
            fields = ["summary", "description", "status", "assignee", "issuetype", "created", "updated"]

        response_data = await self.client.post(
            "/rest/api/3/search",
            user_id,
            {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": fields
            },
            error_msg="Error when searching issues"
        )

        issues = []
        for issue_data in response_data.get("issues", []):
            issue = await self.client.map_to_domain(
                issue_data,
                JiraAPIIssueResponse,
                JiraIssueMapper
            )
            issues.append(issue)

        return issues

    async def get_issue_transitions(self, user_id: int, issue_id: str) -> List[Dict[str, Any]]:
        """Get list of possible transitions for issue"""
        response_data = await self.client.get(
            f"/rest/api/3/issue/{issue_id}/transitions",
            user_id,
            error_msg=f"Error when getting list of transitions for issue {issue_id}"
        )

        return response_data.get("transitions", [])

    async def transition_issue(self, user_id: int, issue_id: str, status: JiraIssueStatus) -> None:
        """Perform transition for issue"""
        # Get list of possible transitions
        transitions = await self.get_issue_transitions(user_id, issue_id)

        # Find transition ID corresponding to status
        transition_id = None
        for transition in transitions:
            if transition.get("name") == status.value or transition.get("to", {}).get("name") == status.value:
                transition_id = transition.get("id")
                break

        if not transition_id:
            log.warning(f"No transition found for status {status.value} of issue {issue_id}")
            return

        # Perform transition
        await self.client.post(
            f"/rest/api/3/issue/{issue_id}/transitions",
            user_id,
            {"transition": {"id": transition_id}},
            error_msg=f"Error when transitioning issue {issue_id} to {status.value}"
        )

    async def add_comment(self, user_id: int, issue_id: str, comment: str) -> Dict[str, Any]:
        """Add comment to issue"""
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": comment
                            }
                        ]
                    }
                ]
            }
        }

        return await self.client.post(
            f"/rest/api/3/issue/{issue_id}/comment",
            user_id,
            payload,
            error_msg=f"Error when adding comment to issue {issue_id}"
        )

    async def get_issue_history(self, user_id: int, issue_id: str) -> List[Dict[str, Any]]:
        """Get issue history"""
        response_data = await self.client.get(
            f"/rest/api/3/issue/{issue_id}/changelog",
            user_id,
            error_msg=f"Error when getting issue history for issue {issue_id}"
        )

        return response_data.get("values", [])

    def _text_to_adf(self, text: str) -> Dict[str, Any]:
        """Convert plain text to Atlassian Document Format"""
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                }
            ]
        }
