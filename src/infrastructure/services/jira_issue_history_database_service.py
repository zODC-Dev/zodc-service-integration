from datetime import datetime
from typing import List, Optional

from src.configs.logger import log
from src.domain.models.jira_issue_history import IssueHistoryEventModel, JiraIssueHistoryModel
from src.domain.repositories.jira_issue_history_repository import IJiraIssueHistoryRepository
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService


class JiraIssueHistoryDatabaseService(IJiraIssueHistoryDatabaseService):
    """Service xử lý lịch sử issue sử dụng repository"""

    def __init__(self, history_repository: IJiraIssueHistoryRepository):
        self.history_repository = history_repository

    async def get_issue_history(
        self,
        issue_id: int
    ) -> List[JiraIssueHistoryModel]:
        """Lấy toàn bộ lịch sử thay đổi của một issue"""
        return await self.history_repository.get_issue_history(issue_id)

    async def get_issue_field_history(
        self,
        issue_id: int,
        field_name: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của một trường cụ thể"""
        return await self.history_repository.get_issue_field_history(issue_id, field_name)

    async def get_issue_status_changes(
        self,
        issue_id: int
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi trạng thái của issue"""
        return await self.get_issue_field_history(issue_id, "status")

    async def get_issue_sprint_changes(
        self,
        issue_id: int
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi sprint của issue"""
        return await self.get_issue_field_history(issue_id, "sprint")

    async def save_issue_history_event(
        self,
        event: IssueHistoryEventModel
    ) -> None:
        """Lưu một sự kiện thay đổi issue"""
        try:
            success = await self.history_repository.save_history_event(event)

            if not success:
                raise Exception("Failed to save history event")
        except Exception as e:
            log.error(f"Error saving issue history event: {str(e)}")
            raise Exception(f"Error saving issue history event: {str(e)}") from e

    async def get_sprint_issue_histories(
        self,
        sprint_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của tất cả issue trong một sprint"""
        return await self.history_repository.get_sprint_issue_histories(sprint_id, from_date, to_date)
