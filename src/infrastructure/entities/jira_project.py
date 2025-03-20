from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_issue import JiraIssueEntity

from .base import BaseEntityWithTimestamps


class JiraProjectEntity(BaseEntityWithTimestamps, table=True):
    __tablename__ = "projects"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(unique=True, index=True)
    jira_project_id: str = Field(unique=True, index=True)
    name: str = Field(unique=True, index=True)
    key: str = Field(unique=True, index=True)
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    is_jira_linked: bool = Field(default=False)
    jira_issues: List["JiraIssueEntity"] = Relationship(back_populates="project")
