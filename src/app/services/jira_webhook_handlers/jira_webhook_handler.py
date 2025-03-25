from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.configs.logger import log
from src.domain.models.jira.webhooks.jira_webhook import JiraWebhookResponseDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService


class JiraWebhookHandler(ABC):
    """Base class for Jira webhook handlers"""

    def __init__(
        self,
        jira_issue_repository: IJiraIssueRepository,
        sync_log_repository: ISyncLogRepository,
        jira_issue_api_service: IJiraIssueAPIService
    ):
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository
        self.jira_issue_api_service = jira_issue_api_service

    @abstractmethod
    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        pass

    @abstractmethod
    async def handle(self, webhook_data: JiraWebhookResponseDTO) -> Dict[str, Any]:
        """Handle the webhook"""
        pass

    async def get_latest_issue_data(self, issue_id: str) -> Optional[JiraIssueModel]:
        """Get latest issue data from Jira API"""
        return await self.jira_issue_api_service.get_issue_with_system_user(issue_id)

    async def process(self, webhook_data: JiraWebhookResponseDTO) -> Optional[Dict[str, Any]]:
        """Process the webhook if this handler can handle it"""
        try:
            event_type = webhook_data.webhook_event

            if not await self.can_handle(event_type):
                return None

            log.info(f"Processing webhook event {event_type} with handler {self.__class__.__name__}")
            result = await self.handle(webhook_data)
            log.info(f"Successfully processed webhook event {event_type}")
            return result

        except Exception as e:
            log.error(f"Error processing webhook: {str(e)}")
            raise
