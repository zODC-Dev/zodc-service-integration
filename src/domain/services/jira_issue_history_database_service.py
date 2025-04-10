from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.domain.models.database.jira_issue_history import JiraIssueHistoryDBCreateDTO
from src.domain.models.jira_issue_history import JiraIssueHistoryModel


class IJiraIssueHistoryDatabaseService(ABC):
    """Interface cho service xử lý lịch sử issue"""

    @abstractmethod
    async def get_issue_history(
        self,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy toàn bộ lịch sử thay đổi của một issue"""
        pass

    @abstractmethod
    async def get_issue_field_history(
        self,
        jira_issue_id: str,
        field_name: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của một trường cụ thể"""
        pass

    @abstractmethod
    async def get_issue_status_changes(
        self,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi trạng thái của issue"""
        pass

    @abstractmethod
    async def get_issue_sprint_changes(
        self,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi sprint của issue"""
        pass

    @abstractmethod
    async def save_issue_history_event(
        self,
        event: JiraIssueHistoryDBCreateDTO
    ) -> None:
        """Lưu một sự kiện thay đổi issue"""
        pass

    @abstractmethod
    async def get_sprint_issue_histories(
        self,
        sprint_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của tất cả issue trong một sprint"""
        pass
