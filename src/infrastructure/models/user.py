from typing import Optional

from sqlmodel import Field

from .base import BaseModelWithTimestamps


class User(BaseModelWithTimestamps, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    user_id: int = Field(unique=True, index=True)
    jira_account_id: Optional[str] = Field(default=None)
    is_system_user: bool = Field(default=False)
