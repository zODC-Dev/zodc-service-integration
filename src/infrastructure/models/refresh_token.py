from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from src.domain.constants.refresh_tokens import TokenType


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="jira_users.user_id")
    token_type: TokenType = Field(...)
    expires_at: datetime
    is_revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)
