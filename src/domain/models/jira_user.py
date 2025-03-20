from typing import Optional

from pydantic import BaseModel, EmailStr

from .base import BaseDomainModel


class JiraUserModel(BaseDomainModel):
    id: Optional[int] = None
    email: EmailStr
    user_id: int
    jira_account_id: Optional[str] = None
    is_system_user: bool = False


class JiraUserCreateDTO(BaseModel):
    email: EmailStr
    user_id: int
    jira_account_id: Optional[str] = None
    is_system_user: bool = False


class JiraUserUpdateDTO(BaseModel):
    email: Optional[EmailStr] = None
    jira_account_id: Optional[str] = None
    is_system_user: Optional[bool] = None
