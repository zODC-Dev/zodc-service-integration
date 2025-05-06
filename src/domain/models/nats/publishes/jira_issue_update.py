from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer

from src.domain.constants.nats_events import NATSPublishTopic
from src.domain.models.nats.publishes.nats import NATSPublishDTO


class JiraIssueUpdateDataPublishDTO(BaseModel):
    """Model for Jira issue update data to be sent to masterflow"""
    jira_key: str = Field(..., description="Jira issue key", alias="jiraKey")
    summary: str = Field(..., description="Jira issue summary", alias="summary")
    description: Optional[str] = Field(None, description="Jira issue description", alias="description")
    assignee_mail: Optional[str] = Field(None, description="Jira issue assignee email", alias="assigneeEmail")
    assignee_id: Optional[str] = Field(None, description="System user id of assignee", alias="assigneeId")
    sprint_id: Optional[int] = Field(None, description="Jira sprint id", alias="sprintId")
    estimate_point: Optional[float] = Field(None, description="Jira issue estimate point", alias="estimatePoint")
    status: str = Field(..., description="Jira issue status", alias="status")
    old_status: Optional[str] = Field(None, description="Jira issue old status", alias="oldStatus")
    last_synced_at: Optional[datetime] = Field(None, description="Last synced at", alias="lastSyncedAt")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True

    @field_serializer("last_synced_at")
    def serialize_last_synced_at(self, last_synced_at: datetime, _info: Any) -> str:
        return last_synced_at.isoformat() if last_synced_at else None


class JiraIssueUpdatePublishDTO(NATSPublishDTO):
    """DTO for publishing Jira issue updates to NATS"""

    @classmethod
    def create(cls, issue_data: JiraIssueUpdateDataPublishDTO) -> "JiraIssueUpdatePublishDTO":
        """Create a DTO for publishing Jira issue update event"""
        return cls(
            subject=NATSPublishTopic.JIRA_ISSUE_UPDATE,
            event_type="jira_issue_updated",
            data=issue_data.model_dump(exclude_none=True, by_alias=True),
        )
