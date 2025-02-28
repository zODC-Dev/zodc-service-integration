from typing import Optional

from pydantic import BaseModel

from .base import BaseEntity


class Project(BaseEntity):
    project_id: int
    name: str
    key: str
    jira_project_id: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    project_id: int
    name: str
    key: str
    jira_project_id: str
    avatar_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    key: Optional[str] = None
    description: Optional[str] = None
