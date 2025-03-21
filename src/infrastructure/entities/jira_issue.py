from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import DateTime, Field, Relationship

from src.infrastructure.entities.base import BaseEntityWithTimestamps

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_project import JiraProjectEntity
    from src.infrastructure.entities.jira_sprint import JiraSprintEntity
    from src.infrastructure.entities.jira_user import JiraUserEntity


class JiraIssueEntity(BaseEntityWithTimestamps, table=True):
    __tablename__ = "jira_issues"

    id: Optional[int] = Field(default=None, primary_key=True)
    jira_issue_id: str = Field(index=True, unique=True)
    key: str = Field(unique=True)
    summary: str
    description: Optional[str] = None
    status: str  # Will store JiraIssueStatus.value
    type: str  # Will store JiraIssueType.value
    priority_id: Optional[str] = None
    estimate_point: float = Field(default=0)
    actual_point: Optional[float] = None
    project_key: str = Field(foreign_key="jira_projects.key")
    reporter_id: Optional[str] = Field(default=None, foreign_key="jira_users.jira_account_id")
    last_synced_at: datetime = Field(sa_type=DateTime(timezone=True))
    updated_locally: bool = Field(default=False)
    sprint_id: int = Field(default=None, foreign_key="jira_sprints.jira_sprint_id")
    assignee_id: Optional[str] = Field(default=None, foreign_key="jira_users.jira_account_id")
    created_at: datetime = Field(sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(sa_type=DateTime(timezone=True))

    project: "JiraProjectEntity" = Relationship(back_populates="jira_issues")
    sprint: Optional["JiraSprintEntity"] = Relationship(back_populates="issues")
    assignee: Optional["JiraUserEntity"] = Relationship(
        back_populates="assigned_issues",
        sa_relationship_kwargs={"foreign_keys": "[JiraIssueEntity.assignee_id]"}
    )
    reporter: Optional["JiraUserEntity"] = Relationship(
        back_populates="reported_issues",
        sa_relationship_kwargs={"foreign_keys": "[JiraIssueEntity.reporter_id]"}
    )
