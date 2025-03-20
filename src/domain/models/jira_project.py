from typing import Optional

from pydantic import BaseModel

from src.domain.constants.jira import JiraSprintState

from .base import BaseDomainModel


class JiraProjectModel(BaseDomainModel):
    project_id: int
    name: str
    key: str
    jira_project_id: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    is_jira_linked: bool = False

    class Config:
        from_attributes = True


class JiraSprintModel(BaseDomainModel):
    id: int
    name: str
    state: JiraSprintState


class JiraProjectCreateDTO(BaseModel):
    project_id: int
    name: str
    key: str
    jira_project_id: str
    avatar_url: Optional[str] = None


class JiraProjectUpdateDTO(BaseModel):
    name: Optional[str] = None
    key: Optional[str] = None
    description: Optional[str] = None
