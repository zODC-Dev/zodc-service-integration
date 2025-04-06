from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class JiraUserDBCreateDTO(BaseModel):
    """DTO for creating a new Jira user in database"""
    user_id: Optional[int] = None
    jira_account_id: Optional[str] = None
    name: str
    email: str = ""
    is_active: bool = True
    avatar_url: str = ""
    is_system_user: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JiraUserDBUpdateDTO(BaseModel):
    """DTO for updating a Jira user in database"""
    user_id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    jira_account_id: Optional[str] = None
    is_system_user: Optional[bool] = None
    avatar_url: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
