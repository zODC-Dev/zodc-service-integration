from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_issue import JiraIssueEntity
    from src.infrastructure.entities.jira_issue_history import JiraIssueHistoryEntity
    from src.infrastructure.entities.jira_project import JiraProjectEntity


class JiraUserEntity(SQLModel, table=True):
    __tablename__ = "jira_users"

    id: Optional[int] = Field(default=None, primary_key=True)  # Auto incremented id
    email: str = Field(unique=True, index=True)
    user_id: Optional[int] = Field(default=None, unique=True, index=True)  # System user id
    jira_account_id: Optional[str] = Field(default=None, index=True, unique=True)  # Jira account id
    is_system_user: bool = Field(default=False)
    is_active: bool = Field(default=True)
    avatar_url: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Relationships
    assigned_issues: List["JiraIssueEntity"] = Relationship(
        back_populates="assignee",
        sa_relationship_kwargs={"foreign_keys": "[JiraIssueEntity.assignee_id]"}
    )
    reported_issues: List["JiraIssueEntity"] = Relationship(
        back_populates="reporter",
        sa_relationship_kwargs={"foreign_keys": "[JiraIssueEntity.reporter_id]"}
    )

    projects: List["JiraProjectEntity"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "[JiraProjectEntity.user_id]"}
    )

    issue_histories: List["JiraIssueHistoryEntity"] = Relationship(
        back_populates="author",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
