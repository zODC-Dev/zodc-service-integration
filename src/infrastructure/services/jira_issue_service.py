from datetime import datetime, timezone
from typing import Any, Dict

import aiohttp
from aiohttp import ClientTimeout

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.refresh_tokens import TokenType
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.exceptions.jira_exceptions import JiraAuthenticationError, JiraRequestError
from src.domain.models.jira_issue import (
    JiraIssueCreateDTO,
    JiraIssueModel,
    JiraIssueStatus,
    JiraIssueUpdateDTO,
)
from src.domain.models.sync_log import SyncLogCreateDTO
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_scheduler_service import ITokenSchedulerService
from src.infrastructure.dtos.jira.issue_responses import JiraAPIIssueResponse
from src.infrastructure.mappers.jira_issue_mapper import JiraIssueMapper


class JiraIssueService(IJiraIssueDatabaseService):
    def __init__(
        self,
        redis_service: IRedisService,
        token_scheduler_service: ITokenSchedulerService,
        user_repository: IJiraUserRepository,
        sync_log_repository: ISyncLogRepository,
    ):
        self.redis_service = redis_service
        self.token_scheduler_service = token_scheduler_service
        self.user_repository = user_repository
        self.timeout = ClientTimeout(total=30)
        self.base_url = settings.JIRA_BASE_URL
        self.sync_log_repository = sync_log_repository

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

    async def get_issue(self, user_id: int, issue_id: str) -> JiraIssueModel:
        token = await self._get_token(user_id)

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    f"{settings.JIRA_BASE_URL}/rest/api/3/issue/{issue_id}",
                    headers=self._get_headers(token)
                ) as response:
                    if response.status != 200:
                        raise JiraRequestError(response.status, "Failed to fetch issue")

                    data = await response.json()
                    api_response = JiraAPIIssueResponse.model_validate(data)
                    return JiraIssueMapper.to_domain_issue(api_response)

        except Exception as e:
            raise JiraRequestError(500, f"Failed to fetch issue: {str(e)}") from e

    async def update_issue(self, user_id: int, issue_id: str, update: JiraIssueUpdateDTO) -> JiraIssueModel:
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

        return JiraIssueModel(
            id=issue_id,
            key=issue_id,
            self_url=f"{self.base_url}/rest/api/3/issue/{issue_id}"
        )

    def _get_headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def create_issue(self, user_id: int, issue: JiraIssueCreateDTO) -> JiraIssueModel:
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
                response_body = await response.json()

                # Log the sync operation
                await self.sync_log_repository.create_sync_log(
                    SyncLogCreateDTO(
                        entity_type=EntityType.ISSUE,
                        entity_id=response_body.get("key", ""),
                        operation=OperationType.CREATE,
                        request_payload=payload,
                        response_status=response.status,
                        response_body=response_body,
                        source=SourceType.MANUAL,
                        sender=user_id,
                        error_message=None if response.status == 201 else await response.text()
                    )
                )

                if response.status != 201:
                    raise Exception(f"Failed to create Jira issue: {response.status} - {await response.text()}")

                # Create the issue model
                return JiraIssueModel(
                    key=response_body["key"],
                    summary=issue.summary,
                    description=issue.description,
                    status=JiraIssueStatus.TO_DO,  # Default status for new issues
                    type=issue.issue_type,
                    estimate_point=issue.estimate_points or 0,
                    actual_point=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    jira_issue_id=response_body["id"],
                    project_key=issue.project_key,
                    last_synced_at=datetime.now(timezone.utc),
                    reporter_id=user_id
                )
