from datetime import datetime, timezone
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class JiraBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allow both snake_case and camelCase input fields
        from_attributes=True
    )


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
    assignee: Optional['JiraUserModel'] = None
    assignee_id: Optional[str] = None  # Add assignee_id field
    priority: Optional['JiraIssuePriorityModel'] = None
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

    class Config:
        from_attributes = True


class JiraIssueCreateDTO(BaseModel):
    jira_issue_id: str
    key: str
    project_key: str
    summary: str
    description: Optional[str] = None
    type: str
    estimate_point: Optional[float] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    reporter_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    link_url: Optional[str] = None

    @classmethod
    def _to_domain(cls, entity: 'JiraIssueCreateDTO') -> "JiraIssueModel":
        return JiraIssueModel(
            jira_issue_id=entity.jira_issue_id,
            key=entity.key,
            project_key=entity.project_key,
            summary=entity.summary,
            description=entity.description,
            type=JiraIssueType(entity.type),
            assignee_id=entity.assignee_id,
            estimate_point=entity.estimate_point or 0,
            status=JiraIssueStatus(entity.status),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            reporter_id=entity.reporter_id,
            last_synced_at=datetime.now(timezone.utc),
            updated_locally=False,
            is_system_linked=False,
            is_deleted=False,
            link_url=entity.link_url,
        )

    @classmethod
    def _from_domain(cls, domain: 'JiraIssueModel') -> 'JiraIssueCreateDTO':
        return cls(
            jira_issue_id=domain.jira_issue_id,
            key=domain.key,
            project_key=domain.project_key,
            summary=domain.summary,
            type=domain.type.value if domain.type else None,
            description=domain.description,
            estimate_point=domain.estimate_point,
            status=domain.status.value if domain.status else None,
            assignee_id=domain.assignee_id,
            reporter_id=domain.reporter_id,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
            link_url=domain.link_url,
        )


class JiraIssueUpdateDTO(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Union[JiraIssueStatus, str]] = None
    assignee: Optional[str] = None
    estimate_point: Optional[float] = None
    actual_point: Optional[float] = None
    last_synced_at: Optional[datetime] = None
    updated_locally: Optional[bool] = None
    is_system_linked: Optional[bool] = None
    assignee_id: Optional[str] = None
    reporter_id: Optional[str] = None
    sprints: Optional[List['JiraSprintModel']] = None
    is_deleted: Optional[bool] = None
    type: Optional[Union[JiraIssueType, str]] = None

    @field_validator('status')
    def validate_status(self, v):
        if v is None:
            return None
        if isinstance(v, JiraIssueStatus):
            return v
        try:
            return JiraIssueStatus(v)
        except ValueError as e:
            raise ValueError(f"Invalid status: {v}") from e

    @field_validator('type')
    def validate_type(self, v):
        if v is None:
            return None
        if isinstance(v, JiraIssueType):
            return v
        try:
            return JiraIssueType(v)
        except ValueError as e:
            raise ValueError(f"Invalid issue type: {v}") from e

    @classmethod
    def _to_domain(cls, entity: 'JiraIssueUpdateDTO') -> "JiraIssueModel":
        return JiraIssueModel(
            summary=entity.summary,
            description=entity.description,
            status=entity.status,
            assignee_id=entity.assignee_id,
            estimate_point=entity.estimate_point,
            actual_point=entity.actual_point,
            last_synced_at=entity.last_synced_at,
            updated_locally=entity.updated_locally,
            is_system_linked=entity.is_system_linked,
            reporter_id=entity.reporter_id,
            is_deleted=entity.is_deleted,
            type=entity.type,
        )

    @classmethod
    def _from_domain(cls, domain: 'JiraIssueModel') -> 'JiraIssueUpdateDTO':
        return cls(
            summary=domain.summary,
            description=domain.description,
            status=domain.status,
            assignee_id=domain.assignee_id,
            estimate_point=domain.estimate_point,
            actual_point=domain.actual_point,
            last_synced_at=domain.last_synced_at,
            updated_locally=domain.updated_locally,
            is_system_linked=domain.is_system_linked,
            sprints=domain.sprints,
            reporter_id=domain.reporter_id,
            is_deleted=domain.is_deleted,
            type=domain.type,
        )
