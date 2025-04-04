from datetime import datetime
import json
from typing import Any, List, Optional

from pydantic import BaseModel

from src.configs.logger import log
from src.domain.models.base import BaseModel as DomainBaseModel


class JiraIssueHistoryModel(DomainBaseModel):
    """Domain model cho lịch sử thay đổi của issue"""
    id: Optional[int] = None
    jira_issue_id: str
    field_name: str
    field_type: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    old_string: Optional[str] = None
    new_string: Optional[str] = None
    author_id: Optional[str] = None
    created_at: datetime
    jira_change_id: Optional[str] = None

    @property
    def old_value_parsed(self) -> Any:
        """Parse giá trị cũ dựa trên field_type"""
        if not self.old_value:
            return None

        if self.field_type == "number":
            return float(self.old_value) if self.old_value else None
        elif self.field_type == "array" or self.field_type == "object":
            try:
                return json.loads(self.old_value)
            except Exception as e:
                log.error(f"Error parsing old value: {str(e)}")
                return self.old_value
        return self.old_value

    @property
    def new_value_parsed(self) -> Any:
        """Parse giá trị mới dựa trên field_type"""
        if not self.new_value:
            return None

        if self.field_type == "number":
            return float(self.new_value) if self.new_value else None
        elif self.field_type == "array" or self.field_type == "object":
            try:
                return json.loads(self.new_value)
            except Exception as e:
                log.error(f"Error parsing new value: {str(e)}")
                return self.new_value
        return self.new_value


class IssueHistoryChangeModel(BaseModel):
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


class IssueHistoryEventModel(BaseModel):
    """Model cho sự kiện thay đổi issue từ webhook hoặc API"""
    jira_issue_id: str
    jira_change_id: str
    author_id: Optional[str] = None
    created_at: datetime
    changes: List[IssueHistoryChangeModel]
