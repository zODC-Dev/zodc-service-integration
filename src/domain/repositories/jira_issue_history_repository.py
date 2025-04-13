from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from src.domain.models.database.jira_issue_history import JiraIssueHistoryDBCreateDTO
from src.domain.models.jira_issue_history import JiraIssueHistoryModel


class IJiraIssueHistoryRepository(ABC):
    """Interface cho repository lưu trữ và truy xuất lịch sử thay đổi của Jira issue"""

    @abstractmethod
    async def get_issues_field_history(
        self,
        jira_issue_ids: List[str],
        field_name: str
    ) -> Dict[str, List[JiraIssueHistoryModel]]:
        """Lấy lịch sử thay đổi của tất cả issue trong một sprint"""
        pass

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
        issue_id: str,  # Lưu ý: Cần chuyển đổi thành string khi truy vấn database
        field_name: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của một trường cụ thể"""
        pass

    @abstractmethod
    async def create(
        self,
        event: JiraIssueHistoryDBCreateDTO
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
