from typing import Dict, Optional, Union

from src.infrastructure.dtos.jira.base import JiraAPIResponseBase


class JiraAPIUserResponse(JiraAPIResponseBase):
    accountId: str
    emailAddress: Optional[str] = None
    displayName: str
    active: bool = True
    timeZone: Optional[str] = None
    avatarUrls: Union[Dict[str, str], str, None] = None

    class Config:
        extra = "allow"
