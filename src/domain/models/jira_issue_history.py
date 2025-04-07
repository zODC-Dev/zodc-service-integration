from datetime import datetime
import json
from typing import Any, Optional

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
