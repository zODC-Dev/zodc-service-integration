from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from src.domain.constants.nats_events import NATSSubscribeTopic


class JiraUserLoginNATSSubscribeDTO(BaseModel):
    user_id: int
    email: str
    jira_account_id: str
    is_system_user: bool
    access_token: str
    refresh_token: str
    expires_in: int


class MicrosoftUserLoginNATSSubscribeDTO(BaseModel):
    user_id: int
    email: str
    access_token: str
    refresh_token: str
    expires_in: int


class JiraUserChangeNATSSubscribeDTO(BaseModel):
    """Jira user change event"""
    event_type: NATSSubscribeTopic
    user_id: int
    timestamp: datetime
    data: Optional[Dict[str, Any]] = None
