from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, List

from pydantic import BaseModel

from src.domain.constants.nats_events import NATSSubscribeTopic
from src.domain.constants.refresh_tokens import TokenType


class UserEvent(BaseModel):
    event_type: NATSSubscribeTopic
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


class ProjectLinkEvent(BaseModel):
    project_id: int
    jira_project_id: str
    name: str
    key: str
    avatar_url: Optional[str] = None


class ProjectUnlinkEvent(BaseModel):
    project_id: str
    jira_project_id: str


class JiraUserInfo(BaseModel):
    jira_account_id: str
    email: str
    name: str


class JiraUsersRequestEvent(BaseModel):
    admin_user_id: int
    project_id: int
    jira_project_id: str
    key: str


class JiraUsersResponseEvent(BaseModel):
    project_id: int
    jira_project_id: str
    users: List[JiraUserInfo]
