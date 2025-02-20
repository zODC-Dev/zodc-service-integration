from typing import Optional

from sqlmodel import Field, SQLModel

from .base import BaseModelWithTimestamps


class User(BaseModelWithTimestamps, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    user_id: str = Field(unique=True, index=True)
    jira_account_id: Optional[str] = Field(default=None)
    is_jira_linked: bool = Field(default=False)
