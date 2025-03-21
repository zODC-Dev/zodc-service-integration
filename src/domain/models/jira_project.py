from typing import Optional

from pydantic import BaseModel


class JiraProjectModel(BaseModel):
    id: Optional[int] = None          # ID trong database của chúng ta
    project_id: Optional[int] = None  # ID trong database (alias cho id)
    jira_project_id: str             # ID từ Jira API (e.g. '10002')
    key: str                         # Project key (e.g. 'STEM')
    name: str
    description: str = ""
    avatar_url: str = ""

    class Config:
        from_attributes = True


class JiraProjectCreateDTO(BaseModel):
    jira_project_id: str             # ID từ Jira API
    key: str
    name: str
    description: str = ""
    avatar_url: str = ""


class JiraProjectUpdateDTO(BaseModel):
    project_id: Optional[int] = None
    key: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    description: Optional[str] = None
