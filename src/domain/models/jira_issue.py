from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue_history import JiraIssueHistoryModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class JiraBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allow both snake_case and camelCase input fields
        from_attributes=True
    )


class JiraIssueModel(BaseModel):
    id: Optional[int] = None
    key: str
    summary: str
    description: Optional[str] = None
    status: JiraIssueStatus
    assignee: Optional['JiraUserModel'] = None
    assignee_id: Optional[str] = None  # Add assignee_id field
    priority: Optional[str] = None
    reporter: Optional['JiraUserModel'] = None
    type: JiraIssueType
    sprints: List['JiraSprintModel'] = Field(default_factory=list)
    estimate_point: float = Field(default=0)
    actual_point: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    jira_issue_id: str
    project_key: str
    reporter_id: Optional[str] = None
    last_synced_at: datetime
    updated_locally: bool = Field(default=False)
    is_system_linked: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    link_url: Optional[str] = None
    history_items: Optional[List[JiraIssueHistoryModel]] = None
    planned_start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    story_id: Optional[str] = None

    class Config:
        from_attributes = True
