from typing import Dict, Optional

from pydantic import BaseModel, Field


class JiraUserAPIGetResponseDTO(BaseModel):
    """DTO for user response from Jira API"""
    account_id: str = Field(alias="accountId")
    account_type: str = Field(alias="accountType")
    active: bool
    display_name: str = Field(alias="displayName")
    email_address: Optional[str] = Field(None, alias="emailAddress")
    avatar_urls: Optional[Dict[str, str]] = Field(None, alias="avatarUrls")

    class Config:
        populate_by_name = True
