from typing import Optional

from pydantic import BaseModel, Field


class JiraLocationDTO(BaseModel):
    """DTO for location information in Jira Board API response"""
    display_name: Optional[str] = Field(None, alias="displayName")
    name: Optional[str] = None
    project_id: Optional[int] = Field(None, alias="projectId")
    project_key: Optional[str] = Field(None, alias="projectKey")
    project_name: Optional[str] = Field(None, alias="projectName")
    project_type_key: Optional[str] = Field(None, alias="projectTypeKey")
    user_account_id: Optional[str] = Field(None, alias="userAccountId")
    user_id: Optional[int] = Field(None, alias="userId")


class JiraBoardAPIGetResponseDTO(BaseModel):
    """DTO for Jira Board API response"""
    id: int
    name: str
    type: str
    location: Optional[JiraLocationDTO] = None
    self_link: Optional[str] = Field(None, alias="self")

    class Config:
        populate_by_name = True
