from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import Field

from .base import JiraAPIResponseBase


class JiraAPIUserResponse(JiraAPIResponseBase):
    account_id: str = Field(alias="accountId")
    email_address: Optional[str] = Field(alias="emailAddress")
    display_name: str = Field(alias="displayName")
    active: bool
    avatar_urls: Dict[str, str] = Field(alias="avatarUrls")
    account_type: Optional[str] = Field(alias="accountType", default=None)


class JiraAPISprintResponse(JiraAPIResponseBase):
    id: int
    name: str
    state: str
    start_date: Optional[datetime] = Field(alias="startDate")
    end_date: Optional[datetime] = Field(alias="endDate")
    goal: Optional[str]


class JiraAPIProjectBaseResponse(JiraAPIResponseBase):
    id: str
    key: str
    name: str
    description: Optional[str] = None
    project_type_key: str = Field(alias="projectTypeKey")
    project_category: Optional[Dict[str, Any]] = Field(alias="projectCategory")
    lead: Optional[Dict[str, str]]
    url: Optional[str] = Field(alias="self")
    avatar_urls: Dict[str, str] = Field(alias="avatarUrls")
