from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

from src.infrastructure.entities.jira_issue_history import JiraIssueHistoryEntity
from src.infrastructure.entities.jira_issue_sprint import JiraIssueSprintEntity

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_project import JiraProjectEntity
    from src.infrastructure.entities.jira_sprint import JiraSprintEntity
    from src.infrastructure.entities.jira_user import JiraUserEntity


class JiraIssueEntity(SQLModel, table=True):
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
    last_synced_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    updated_locally: bool = Field(default=False)
    assignee_id: Optional[str] = Field(default=None, foreign_key="jira_users.jira_account_id")
    is_system_linked: bool = Field(default=False)
    is_deleted: bool = Field(default=False)
    link_url: Optional[str] = Field(default=None)
    planned_start_time: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    planned_end_time: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    actual_start_time: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    actual_end_time: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
    # Story ID to which this issue belongs to
    story_id: Optional[str] = Field(default=None, foreign_key="jira_issues.jira_issue_id")

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    project: "JiraProjectEntity" = Relationship(
        back_populates="jira_issues", sa_relationship_kwargs={'lazy': 'selectin'})
    sprints: List["JiraSprintEntity"] = Relationship(
        back_populates="issues",
        link_model=JiraIssueSprintEntity,
        sa_relationship_kwargs={'lazy': 'selectin'}
    )
    assignee: Optional["JiraUserEntity"] = Relationship(
        back_populates="assigned_issues",
        sa_relationship_kwargs={"foreign_keys": "[JiraIssueEntity.assignee_id]", "lazy": "selectin"}
    )
    reporter: Optional["JiraUserEntity"] = Relationship(
        back_populates="reported_issues",
        sa_relationship_kwargs={"foreign_keys": "[JiraIssueEntity.reporter_id]", "lazy": "selectin"}
    )
    histories: List["JiraIssueHistoryEntity"] = Relationship(
        back_populates="issue",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
