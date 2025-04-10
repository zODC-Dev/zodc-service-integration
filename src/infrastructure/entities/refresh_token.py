from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Column, DateTime, Field, SQLModel

from src.domain.constants.refresh_tokens import TokenType


class RefreshTokenEntity(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True, unique=True)
    user_id: int = Field(foreign_key="jira_users.user_id")
    token_type: TokenType = Field(...)
    expires_at: datetime
    is_revoked: bool = Field(default=False)
    # created_at: datetime = Field(default_factory=datetime.now)

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
