from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

from src.infrastructure.entities.jira_issue_sprint import JiraIssueSprintEntity

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_issue import JiraIssueEntity
    from src.infrastructure.entities.jira_project import JiraProjectEntity


class JiraSprintEntity(SQLModel, table=True):
    __tablename__ = "jira_sprints"

    id: Optional[int] = Field(default=None, primary_key=True)
    jira_sprint_id: int = Field(index=True, unique=True)  # ID của sprint từ Jira
    name: str
    state: str  # active, closed, future
    start_date: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True)))
    end_date: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True)))
    complete_date: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True)))
    goal: Optional[str] = None
    board_id: Optional[int] = None
    is_deleted: bool = Field(default=False)

    # Foreign key to project
    project_key: str = Field(foreign_key="jira_projects.key")

    # Relationships
    project: "JiraProjectEntity" = Relationship(back_populates="sprints")
    issues: List["JiraIssueEntity"] = Relationship(
        back_populates="sprints",
        link_model=JiraIssueSprintEntity,
        sa_relationship_kwargs={'lazy': 'selectin'}
    )

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
