from typing import Optional

from pydantic import BaseModel

from src.domain.models.jira_user import JiraUserModel


class JiraProjectModel(BaseModel):
    id: Optional[int] = None          # ID trong database của chúng ta
    project_id: Optional[int] = None  # ID trong database (alias cho id)
    jira_project_id: str             # ID từ Jira API (e.g. '10002')
    key: str                         # Project key (e.g. 'STEM')
    name: str
    description: str = ""
    avatar_url: str = ""
    is_system_linked: bool = False
    user_id: Optional[int] = None

    user: Optional[JiraUserModel] = None

    class Config:
        from_attributes = True
