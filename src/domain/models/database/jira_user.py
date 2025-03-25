from typing import Optional

from pydantic import BaseModel


class JiraUserDBCreateDTO(BaseModel):
    jira_account_id: str
    email: str
    avatar_url: str = ""
    is_system_user: bool = False


class JiraUserDBUpdateDTO(BaseModel):
    email: Optional[str] = None
    jira_account_id: Optional[str] = None
    is_system_user: Optional[bool] = None
    avatar_url: Optional[str] = None
