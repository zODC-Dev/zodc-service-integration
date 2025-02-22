from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from .base import BaseEntity


class User(BaseEntity):
    id: Optional[int] = None
    email: EmailStr
    user_id: int
    jira_account_id: Optional[str] = None
    is_jira_linked: bool = False

    # System-wide role
    jira_token: Optional[str] = None
    jira_refresh_token: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    # Microsoft tokens
    microsoft_access_token: Optional[str] = None
    microsoft_token_expires_at: Optional[datetime] = None

    # Jira tokens
    jira_access_token: Optional[str] = None
    jira_token_expires_at: Optional[datetime] = None


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    microsoft_refresh_token: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    jira_account_id: Optional[str] = None
    is_jira_linked: Optional[bool] = None


class UserWithPassword(User):
    password: str
