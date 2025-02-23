from typing import Optional

from sqlmodel import Field

from .base import BaseModelWithTimestamps


class Project(BaseModelWithTimestamps, table=True):
    __tablename__ = "projects"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(unique=True, index=True)
    jira_project_id: str = Field(unique=True, index=True)
    name: str = Field(unique=True, index=True)
    key: str = Field(unique=True, index=True)
    avatar_url: Optional[str] = None
    is_linked: bool = Field(default=False)
