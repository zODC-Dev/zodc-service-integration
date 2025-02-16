from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class UserEventType(str, Enum):
    ACCESS_TOKEN_UPDATED = "user.access_token.updated"
    REFRESH_TOKEN_UPDATED = "user.refresh_token.updated"
    USER_DEACTIVATED = "user.deactivated"
    USER_ACTIVATED = "user.activated"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_CREATED = "user.created"
    USER_LOGOUT = "user.logout"


class UserEvent(BaseModel):
    event_type: UserEventType
    user_id: int
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None
