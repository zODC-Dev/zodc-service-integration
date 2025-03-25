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
