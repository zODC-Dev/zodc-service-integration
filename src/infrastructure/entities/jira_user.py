from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from .base import BaseEntityWithTimestamps

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_issue import JiraIssueEntity
    from src.infrastructure.entities.jira_project import JiraProjectEntity


class JiraUserEntity(BaseEntityWithTimestamps, table=True):
    __tablename__ = "jira_users"

    id: Optional[int] = Field(default=None, primary_key=True)  # Auto incremented id
    email: str = Field(unique=True, index=True)
    user_id: Optional[int] = Field(default=None, unique=True, index=True)  # System user id
    jira_account_id: Optional[str] = Field(default=None, unique=True, index=True)  # Jira account id
    is_system_user: bool = Field(default=False)
    is_active: bool = Field(default=True)
    avatar_url: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)

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
