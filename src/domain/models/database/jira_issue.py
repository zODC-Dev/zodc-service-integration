from datetime import datetime, timezone
from typing import List, Optional, Union

from pydantic import BaseModel, Field, field_validator

from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.configs.logger import log


class JiraIssueDBCreateDTO(BaseModel):
    jira_issue_id: str
    key: str
    project_key: str
    summary: str
    description: Optional[str] = None
    type: Optional[Union[JiraIssueType, str]] = None
    status: Optional[Union[JiraIssueStatus, str]] = None
    assignee_id: Optional[str] = None
    reporter_id: Optional[str] = None
    estimate_point: Optional[float] = None
    actual_point: Optional[float] = None
    priority: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)
    sprints: List[JiraSprintModel] = Field(default_factory=list)
    link_url: Optional[str] = None
    is_system_linked: bool = False
    planned_start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    story_id: Optional[str] = None

    @classmethod
    def _to_domain(cls, entity: 'JiraIssueDBCreateDTO') -> "JiraIssueModel":
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
            is_system_linked=entity.is_system_linked,
            is_deleted=False,
            link_url=entity.link_url,
            sprints=entity.sprints,
            priority=entity.priority,
            planned_start_time=entity.planned_start_time,
            planned_end_time=entity.planned_end_time,
            actual_start_time=entity.actual_start_time,
            actual_end_time=entity.actual_end_time,
            story_id=entity.story_id,
        )

    @classmethod
    def _from_domain(cls, domain: 'JiraIssueModel') -> 'JiraIssueDBCreateDTO':
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
            sprints=domain.sprints,
            priority=domain.priority,
            planned_start_time=domain.planned_start_time,
            planned_end_time=domain.planned_end_time,
            actual_start_time=domain.actual_start_time,
            actual_end_time=domain.actual_end_time,
            story_id=domain.story_id,
        )

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return None
        if isinstance(v, JiraIssueStatus):
            return v
        try:
            return JiraIssueStatus(v)
        except ValueError as e:
            raise ValueError(f"Invalid status: {v}") from e

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        if v is None:
            return None
        if isinstance(v, JiraIssueType):
            return v
        try:
            return JiraIssueType(v)
        except ValueError as e:
            raise ValueError(f"Invalid issue type: {v}") from e


class JiraIssueDBUpdateDTO(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    estimate_point: Optional[float] = None
    actual_point: Optional[float] = None
    last_synced_at: Optional[datetime] = None
    updated_locally: Optional[bool] = None
    is_system_linked: Optional[bool] = None
    assignee_id: Optional[str] = None
    reporter_id: Optional[str] = None
    priority: Optional[str] = None
    sprints: Optional[List[JiraSprintModel]] = None
    is_deleted: Optional[bool] = None
    type: Optional[Union[JiraIssueType, str]] = None
    link_url: Optional[str] = None
    updated_at: Optional[datetime] = None
    planned_start_time: Optional[datetime] = None
    planned_end_time: Optional[datetime] = None
    actual_start_time: Optional[datetime] = None
    actual_end_time: Optional[datetime] = None
    story_id: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return None
        if isinstance(v, JiraIssueStatus):
            return v
        try:
            return JiraIssueStatus(v)
        except ValueError as e:
            raise ValueError(f"Invalid status: {v}") from e

    @field_validator('type')
    @classmethod
    def validate_type(cls, v):
        if v is None:
            return None
        if isinstance(v, JiraIssueType):
            return v
        try:
            return JiraIssueType(v)
        except ValueError as e:
            raise ValueError(f"Invalid issue type: {v}") from e

    @classmethod
    def _from_domain(cls, domain: 'JiraIssueModel') -> 'JiraIssueDBUpdateDTO':
        return cls(
            summary=domain.summary,
            description=domain.description,
            status=domain.status,
            assignee_id=domain.assignee_id,
            estimate_point=domain.estimate_point,
            actual_point=domain.actual_point,
            last_synced_at=domain.last_synced_at,
            updated_locally=domain.updated_locally,
            updated_at=domain.updated_at,
            is_system_linked=domain.is_system_linked,
            is_deleted=domain.is_deleted,
            type=domain.type,
            sprints=domain.sprints,
            priority=domain.priority,
            planned_start_time=domain.planned_start_time,
            planned_end_time=domain.planned_end_time,
            actual_start_time=domain.actual_start_time,
            actual_end_time=domain.actual_end_time,
            story_id=domain.story_id,
        )

    @classmethod
    def _merge_with_existing(cls, existing: JiraIssueModel, dto) -> JiraIssueModel:
        """Merge update DTO with existing model"""
        update_dict = dto.model_dump(exclude_none=True)
        log.debug(f"[JIRA_ISSUE_DTO] Merging update: {update_dict}")

        existing_dict = existing.model_dump()
        merged_dict = {**existing_dict, **update_dict}

        # Log specific fields that are important for tracking
        if 'planned_start_time' in update_dict:
            log.info(
                f"[JIRA_ISSUE_DTO] Updating planned_start_time: {existing.planned_start_time} -> {update_dict['planned_start_time']}")

        if 'planned_end_time' in update_dict:
            log.info(
                f"[JIRA_ISSUE_DTO] Updating planned_end_time: {existing.planned_end_time} -> {update_dict['planned_end_time']}")

        if 'story_id' in update_dict:
            log.info(f"[JIRA_ISSUE_DTO] Updating story_id: {existing.story_id} -> {update_dict['story_id']}")

        return JiraIssueModel(**merged_dict)
