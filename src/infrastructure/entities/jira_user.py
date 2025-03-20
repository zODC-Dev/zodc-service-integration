from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

from .base import BaseEntityWithTimestamps

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_issue import JiraIssueEntity


class JiraUserEntity(BaseEntityWithTimestamps, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    user_id: int = Field(unique=True, index=True)
    jira_account_id: Optional[str] = Field(default=None, unique=True, index=True)
    is_system_user: bool = Field(default=False)

    # Split into two separate relationships
    assigned_issues: List["JiraIssueEntity"] = Relationship(
        back_populates="assignee",
        sa_relationship_kwargs={"foreign_keys": "[JiraIssueEntity.assignee_id]"}
    )
    reported_issues: List["JiraIssueEntity"] = Relationship(
        back_populates="reporter",
        sa_relationship_kwargs={"foreign_keys": "[JiraIssueEntity.reporter_id]"}
    )
