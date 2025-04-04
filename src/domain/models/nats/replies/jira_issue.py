from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_serializer

from src.domain.constants.jira import JiraActionType


class JiraIssueSyncNATSReplyDTO(BaseModel):
    success: bool
    action_type: JiraActionType
    issue_id: Optional[str] = None
    error_message: Optional[str] = None
    synced_at: datetime = Field(default_factory=datetime.now)

    @field_serializer("synced_at")
    def serialize_synced_at(self, synced_at: datetime, _info: Any) -> str:
        return synced_at.isoformat()


class JiraIssueBatchSyncNATSReplyDTO(BaseModel):
    results: List[JiraIssueSyncNATSReplyDTO]


class JiraIssueBatchLinkNATSReplyDTO(BaseModel):
    results: List[JiraIssueSyncNATSReplyDTO]
