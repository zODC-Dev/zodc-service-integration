from typing import Optional

from pydantic import BaseModel


class JiraUserModel(BaseModel):
    id: Optional[int] = None
    user_id: Optional[int] = None
    jira_account_id: str
    email: str
    avatar_url: Optional[str] = ""
    is_system_user: bool = False
    name: Optional[str] = ""

    class Config:
        from_attributes = True


class JiraUserCreateDTO(BaseModel):
    jira_account_id: str
    email: str
    avatar_url: str = ""
    is_system_user: bool = False


class JiraUserUpdateDTO(BaseModel):
    email: Optional[str] = None
    jira_account_id: Optional[str] = None
    is_system_user: Optional[bool] = None
    avatar_url: Optional[str] = None
