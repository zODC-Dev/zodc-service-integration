from typing import Dict, Optional, Union

from src.domain.models.jira.apis.responses.base import JiraAPIResponseBase


class JiraUserAPIGetResponseDTO(JiraAPIResponseBase):
    accountId: str
    emailAddress: Optional[str] = None
    displayName: str
    active: bool = True
    timeZone: Optional[str] = None
    avatarUrls: Union[Dict[str, str], str, None] = None

    class Config:
        extra = "allow"
