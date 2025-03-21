from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_sprint import JiraSprintModel


class JiraBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allow both snake_case and camelCase input fields
        from_attributes=True
    )


class JiraAssigneeModel(JiraBaseModel):
    id: Optional[str] = None  # user_id từ bảng user
    jira_account_id: str      # Jira account ID
    email: str
    avatar_url: str
    name: str
    is_system_user: bool


class JiraIssuePriorityModel(JiraBaseModel):
    id: str
    name: str
    icon_url: str


class JiraIssueModel(BaseModel):
    id: Optional[int] = None
    key: str
    summary: str
    description: Optional[str] = None
    status: JiraIssueStatus
    assignee: Optional['JiraAssigneeModel'] = None
    priority: Optional['JiraIssuePriorityModel'] = None
    type: JiraIssueType
    sprint: Optional['JiraSprintModel'] = None
    sprint_id: Optional[int] = None
    estimate_point: float = Field(default=0)
    actual_point: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    jira_issue_id: str
    project_key: str
    reporter_id: Optional[str] = None
    last_synced_at: datetime
    updated_locally: bool = Field(default=False)

    class Config:
        from_attributes = True


class JiraIssueCreateDTO(BaseModel):
    project_key: str
    summary: str
    description: Optional[str] = None
    issue_type: str
    assignee: Optional[str] = None
    estimate_points: Optional[float] = None


class JiraIssueUpdateDTO(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    estimate_points: Optional[float] = None
    actual_points: Optional[float] = None
