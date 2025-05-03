from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.database.jira_issue_history import JiraIssueHistoryDBCreateDTO
from src.domain.models.jira_issue_history import JiraIssueHistoryModel


class IJiraIssueHistoryDatabaseService(ABC):
    """Interface cho service xử lý lịch sử issue"""

    @abstractmethod
    async def get_issue_history(
        self,
        session: AsyncSession,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy toàn bộ lịch sử thay đổi của một issue"""
        pass

    @abstractmethod
    async def get_issue_field_history(
        self,
        session: AsyncSession,
        jira_issue_id: str,
        field_name: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của một trường cụ thể"""
        pass

    @abstractmethod
    async def get_issue_status_changes(
        self,
        session: AsyncSession,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi trạng thái của issue"""
        pass

    @abstractmethod
    async def get_issue_sprint_changes(
        self,
        session: AsyncSession,
        jira_issue_id: str
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi sprint của issue"""
        pass

    @abstractmethod
    async def save_issue_history_event(
        self,
        session: AsyncSession,
        event: JiraIssueHistoryDBCreateDTO
    ) -> None:
        """Lưu một sự kiện thay đổi issue"""
        pass

    @abstractmethod
    async def get_sprint_issue_histories(
        self,
        session: AsyncSession,
        sprint_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[JiraIssueHistoryModel]:
        """Lấy lịch sử thay đổi của tất cả issue trong một sprint"""
        pass

    @abstractmethod
    async def get_issues_field_history(
        self,
        session: AsyncSession,
        issue_ids: List[str],
        field_name: str
    ) -> Dict[str, List[JiraIssueHistoryModel]]:
        """Lấy lịch sử thay đổi của tất cả issue trong một sprint"""
        pass
