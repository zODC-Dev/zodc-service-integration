from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.jira.webhooks.jira_webhook import (
    BaseJiraWebhookDTO,
)
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_user import JiraUserModel
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService
from src.domain.services.jira_user_api_service import IJiraUserAPIService
from src.domain.services.jira_user_database_service import IJiraUserDatabaseService


class JiraWebhookHandler(ABC):
    """Base class for Jira webhook handlers"""

    # Hàm khởi tạo này sẽ được ghi đè bởi các lớp con
    def __init__(
        self,
        jira_issue_repository: Optional[IJiraIssueRepository] = None,
        sync_log_repository: Optional[ISyncLogRepository] = None,
        jira_issue_api_service: Optional[IJiraIssueAPIService] = None,
        sprint_database_service: Optional[IJiraSprintDatabaseService] = None,
        jira_sprint_api_service: Optional[IJiraSprintAPIService] = None,
        jira_user_repository: Optional[IJiraUserRepository] = None,
        jira_user_api_service: Optional[IJiraUserAPIService] = None,
        user_database_service: Optional[IJiraUserDatabaseService] = None,
        jira_issue_history_service: Optional[IJiraIssueHistoryDatabaseService] = None
    ):
        self.jira_issue_repository = jira_issue_repository
        self.sync_log_repository = sync_log_repository
        self.jira_issue_api_service = jira_issue_api_service
        self.sprint_database_service = sprint_database_service
        self.jira_sprint_api_service = jira_sprint_api_service
        self.jira_user_repository = jira_user_repository
        self.jira_user_api_service = jira_user_api_service
        self.user_database_service = user_database_service
        self.jira_issue_history_service = jira_issue_history_service

    @abstractmethod
    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        pass

    @abstractmethod
    async def handle(self, session: AsyncSession, webhook_data: BaseJiraWebhookDTO) -> Dict[str, Any]:
        """Handle the webhook

        Args:
            session: The database session to use for database operations
            webhook_data: The webhook data to process

        Returns:
            A dictionary with the result of the operation
        """
        pass

    async def get_latest_issue_data(self, issue_id: str) -> Optional[JiraIssueModel]:
        """Get latest issue data from Jira API"""
        if self.jira_issue_api_service:
            return await self.jira_issue_api_service.get_issue_with_admin_auth(issue_id)
        return None

    async def process(self, session: AsyncSession, webhook_data: BaseJiraWebhookDTO) -> Optional[Dict[str, Any]]:
        """Process the webhook if this handler can handle it

        Args:
            session: The database session to use for database operations
            webhook_data: The webhook data to process

        Returns:
            The result of the handler or None if the handler can't handle this webhook
        """
        try:
            # Sử dụng normalized_event thay vì tự chuẩn hóa
            event_type = webhook_data.normalized_event

            if not event_type:
                log.error(f"No event type found for webhook data: {webhook_data}")
                return None

            if not await self.can_handle(event_type):
                return None

            result = await self.handle(session, webhook_data)
            return result

        except Exception as e:
            log.error(f"Error processing webhook: {str(e)}")
            raise

    async def get_project_key_for_sprint(self, sprint_id: int) -> Optional[str]:
        """Get project key for a sprint by fetching board information"""
        if not self.jira_sprint_api_service:
            return None

        try:
            # Lấy sprint data sử dụng admin auth
            sprint_data = await self.jira_sprint_api_service.get_sprint_by_id_with_admin_auth(sprint_id)
            if not sprint_data:
                log.error(f"Could not find sprint data for {sprint_id}")
                return None

            # Nếu sprint đã có project_key, dùng luôn
            if sprint_data.project_key:
                return sprint_data.project_key

            # Nếu có origin_board_id, lấy board để lấy project_key
            if not hasattr(sprint_data, 'board_id') or not sprint_data.board_id:
                log.error(f"Sprint {sprint_id} does not have board_id")
                return None

            # Lấy board details để lấy project_key
            board_data = await self.jira_sprint_api_service.get_board_by_id_with_admin_auth(sprint_data.board_id)
            if not board_data:
                log.error(f"Could not find board data for ID {sprint_data.board_id}")
                return None

            return board_data.project_key

        except Exception as e:
            log.error(f"Error getting project key for sprint {sprint_id}: {str(e)}")
            return None

    async def get_user_details_from_api(self, account_id: str) -> Optional[JiraUserModel]:
        """Get user details from Jira API"""
        if self.jira_user_api_service:
            try:
                return await self.jira_user_api_service.get_user_by_account_id_with_admin_auth(account_id)
            except Exception as e:
                log.error(f"Error getting user details from API: {str(e)}")
                return None
        return None
