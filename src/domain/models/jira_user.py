from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class JiraUserModel(BaseModel):
    """Domain model for Jira User"""
    id: Optional[int] = None  # auto increment id
    user_id: Optional[int] = None  # for internal use
    jira_account_id: str  # Jira account ID
    name: str
    email: str = ""
    is_active: bool = True
    avatar_url: Optional[str] = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    is_system_user: bool = False

    class Config:
        from_attributes = True
