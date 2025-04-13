from datetime import datetime
from typing import Dict, List, Optional

from src.configs.logger import log
from src.domain.models.database.jira_issue_history import JiraIssueHistoryDBCreateDTO
from src.domain.models.jira_issue_history import JiraIssueHistoryModel
from src.domain.repositories.jira_issue_history_repository import IJiraIssueHistoryRepository
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService


class JiraIssueHistoryDatabaseService(IJiraIssueHistoryDatabaseService):
    """Service xử lý lịch sử issue sử dụng repository"""

    def __init__(self, history_repository: IJiraIssueHistoryRepository):
        self.history_repository = history_repository

    async def get_issue_history(
        self,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy toàn bộ lịch sử thay đổi của một issue"""
        return await self.history_repository.get_issue_history(jira_issue_id)

    async def get_issue_field_history(
        self,
        jira_issue_id: str,
        field_name: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của một trường cụ thể"""
        return await self.history_repository.get_issue_field_history(jira_issue_id, field_name)

    async def get_issue_status_changes(
        self,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi trạng thái của issue"""
        return await self.get_issue_field_history(jira_issue_id, "status")

    async def get_issue_sprint_changes(
        self,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi sprint của issue"""
        return await self.get_issue_field_history(jira_issue_id, "sprint")

    async def save_issue_history_event(
        self,
        event: JiraIssueHistoryDBCreateDTO
    ) -> None:
        """Lưu một sự kiện thay đổi issue"""
        try:
            success = await self.history_repository.create(event)

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

    async def get_issues_field_history(
        self,
        issue_ids: List[str],
        field_name: str
    ) -> Dict[str, List[JiraIssueHistoryModel]]:
        """Lấy lịch sử thay đổi của tất cả issue trong một sprint"""
        return await self.history_repository.get_issues_field_history(issue_ids, field_name)
