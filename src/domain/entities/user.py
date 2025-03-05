from typing import Optional

from pydantic import BaseModel, EmailStr

from .base import BaseEntity


class User(BaseEntity):
    id: Optional[int] = None
    email: EmailStr
    user_id: int
    jira_account_id: Optional[str] = None
    is_system_user: bool = False


class UserCreate(BaseModel):
    email: EmailStr
    user_id: int
    jira_account_id: Optional[str] = None
    is_system_user: bool = False


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    jira_account_id: Optional[str] = None
    is_system_user: Optional[bool] = None


class UserWithPassword(User):
    password: str
