from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.domain.constants.refresh_tokens import TokenType


class NATSEventType(str, Enum):
    ACCESS_TOKEN_UPDATED = "user.access_token.updated"
    REFRESH_TOKEN_UPDATED = "user.refresh_token.updated"
    USER_DEACTIVATED = "user.deactivated"
    USER_ACTIVATED = "user.activated"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_CREATED = "user.created"
    USER_LOGOUT = "user.logout"
    MICROSOFT_TOKEN_UPDATED = "auth.token.microsoft"
    JIRA_TOKEN_UPDATED = "auth.token.jira"


class UserEvent(BaseModel):
    event_type: NATSEventType
    user_id: int
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None


class TokenEvent(BaseModel):
    user_id: int
    token_type: TokenType
    access_token: str
    refresh_token: str
    created_at: datetime
    expires_at: datetime
    expires_in: int
