from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel


class JiraIssueHistoryChangeDBCreateDTO(BaseModel):
    """Model cho một thay đổi cụ thể trong lịch sử issue"""
    field: str
    field_type: str
    from_value: Optional[Any] = None  # Có thể là bất kỳ kiểu dữ liệu gì
    to_value: Optional[Any] = None    # Có thể là bất kỳ kiểu dữ liệu gì
    from_string: Optional[str] = None  # Luôn là string để hiển thị
    to_string: Optional[str] = None   # Luôn là string để hiển thị

    def get_from_value_as_string(self) -> Optional[str]:
        """Chuyển đổi from_value sang string an toàn"""
        if self.from_value is None:
            return None
        return str(self.from_value)

    def get_to_value_as_string(self) -> Optional[str]:
        """Chuyển đổi to_value sang string an toàn"""
        if self.to_value is None:
            return None
        return str(self.to_value)


class JiraIssueHistoryDBCreateDTO(BaseModel):
    """Model chodatetime thay đổi issue từ webhook hoặc API"""
    jira_issue_id: str
    jira_change_id: str
    author_id: Optional[str] = None
    created_at: datetime
    changes: List[JiraIssueHistoryChangeDBCreateDTO]
