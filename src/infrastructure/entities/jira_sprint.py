from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Column, DateTime, Field, Relationship

from src.infrastructure.entities.base import BaseEntityWithTimestamps
from src.infrastructure.entities.jira_issue_sprint import JiraIssueSprintEntity

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_issue import JiraIssueEntity
    from src.infrastructure.entities.jira_project import JiraProjectEntity


class JiraSprintEntity(BaseEntityWithTimestamps, table=True):
    __tablename__ = "jira_sprints"

    id: Optional[int] = Field(default=None, primary_key=True)
    jira_sprint_id: int = Field(index=True, unique=True)  # ID của sprint từ Jira
    name: str
    state: str  # active, closed, future
    start_date: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True)))
    end_date: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True)))
    complete_date: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True)))
    goal: Optional[str] = None

    # Foreign key to project
    project_key: str = Field(foreign_key="jira_projects.key")

    # Relationships
    project: "JiraProjectEntity" = Relationship(back_populates="sprints")
    issues: List["JiraIssueEntity"] = Relationship(
        back_populates="sprints",
        link_model=JiraIssueSprintEntity,
        sa_relationship_kwargs={'lazy': 'selectin'}
    )

    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    updated_at: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=True)))
