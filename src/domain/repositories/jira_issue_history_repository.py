from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.domain.models.jira_issue_history import IssueHistoryEventModel, JiraIssueHistoryModel


class IJiraIssueHistoryRepository(ABC):
    """Interface cho repository lưu trữ và truy xuất lịch sử thay đổi của Jira issue"""

    @abstractmethod
    async def get_issue_history(
        self,
        issue_id: int
    ) -> List[JiraIssueHistoryModel]:
        """Lấy toàn bộ lịch sử thay đổi của một issue"""
        pass

    @abstractmethod
    async def get_issue_field_history(
        self,
        issue_id: int,
        field_name: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của một trường cụ thể"""
        pass

    @abstractmethod
    async def create_history_item(
        self,
        jira_issue_id: str,
        field_name: str,
        field_type: str,
        old_value: Optional[str],
        new_value: Optional[str],
        old_string: Optional[str],
        new_string: Optional[str],
        author_id: Optional[str],
        created_at: datetime,
        jira_change_id: Optional[str]
    ) -> Optional[JiraIssueHistoryModel]:
        """Tạo một bản ghi lịch sử mới"""
        pass

    @abstractmethod
    async def save_history_event(
        self,
        event: IssueHistoryEventModel
    ) -> bool:
        """Lưu một sự kiện thay đổi issue bao gồm nhiều thay đổi"""
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
