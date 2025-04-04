from typing import Optional

from pydantic import BaseModel


class JiraProjectDBCreateDTO(BaseModel):
    project_id: Optional[int] = None
    jira_project_id: str             # ID từ Jira API
    key: str
    name: str
    description: str = ""
    avatar_url: str = ""
    is_system_linked: bool = False
    user_id: Optional[int] = None


class JiraProjectDBUpdateDTO(BaseModel):
    project_id: Optional[int] = None
    key: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    is_system_linked: Optional[bool] = None
