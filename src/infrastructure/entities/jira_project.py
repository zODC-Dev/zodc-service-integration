from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_issue import JiraIssueEntity
    from src.infrastructure.entities.jira_sprint import JiraSprintEntity
    from src.infrastructure.entities.jira_user import JiraUserEntity



class JiraProjectEntity(SQLModel, table=True):
    __tablename__ = "jira_projects"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: Optional[int] = Field(default=None, unique=True, index=True)
    jira_project_id: str = Field(index=True, unique=True)
    name: str
    key: str = Field(index=True, unique=True)
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    is_system_linked: bool = Field(default=False)
    user_id: int = Field(index=True, foreign_key="jira_users.user_id")

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Relationships
    jira_issues: List["JiraIssueEntity"] = Relationship(back_populates="project")
    sprints: List["JiraSprintEntity"] = Relationship(back_populates="project")
    user: "JiraUserEntity" = Relationship(back_populates="projects")
