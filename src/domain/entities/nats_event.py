from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.domain.constants.jira import JiraActionType
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


class MicrosoftLoginEvent(BaseModel):
    user_id: int
    email: str
    access_token: str
    refresh_token: str
    expires_in: int


class JiraLoginEvent(BaseModel):
    user_id: int
    email: str
    jira_account_id: str
    is_system_user: bool
    access_token: str
    refresh_token: str
    expires_in: int


class JiraIssueSyncPayload(BaseModel):
    action_type: JiraActionType
    issue_id: Optional[str] = None  # Required for updates
    project_key: Optional[str] = None  # Required for creates
    summary: Optional[str] = None
    description: Optional[str] = None
    issue_type: Optional[str] = None  # Required for creates
    status: Optional[str] = None
    assignee: Optional[str] = None
    estimate_points: Optional[float] = None
    actual_points: Optional[float] = None
    user_id: int  # User ID for authentication


class JiraIssueSyncResultPayload(BaseModel):
    success: bool
    issue_id: Optional[str] = None
    action_type: JiraActionType
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
