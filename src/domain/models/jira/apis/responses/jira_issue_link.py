from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class JiraStatusCategoryDTO(BaseModel):
    """DTO for Jira status category"""
    self_url: str = Field(alias="self")
    id: int
    key: str
    color_name: str = Field(alias="colorName")
    name: str


class JiraStatusDTO(BaseModel):
    """DTO for Jira status"""
    self_url: str = Field(alias="self")
    description: str
    icon_url: str = Field(alias="iconUrl")
    name: str
    id: str
    status_category: Optional[JiraStatusCategoryDTO] = Field(default=None, alias="statusCategory")


class JiraPriorityDTO(BaseModel):
    """DTO for Jira priority"""
    self_url: str = Field(alias="self")
    icon_url: str = Field(alias="iconUrl")
    name: str
    id: str


class JiraIssueTypeDTO(BaseModel):
    """DTO for Jira issue type"""
    self_url: str = Field(alias="self")
    id: str
    description: str
    icon_url: str = Field(alias="iconUrl")
    name: str
    subtask: bool
    avatar_id: Optional[int] = Field(default=None, alias="avatarId")
    entity_id: Optional[str] = Field(default=None, alias="entityId")
    hierarchy_level: Optional[int] = Field(default=None, alias="hierarchyLevel")


class LinkedIssueFieldsDTO(BaseModel):
    """DTO for fields of a linked issue"""
    summary: Optional[str] = None
    status: Optional[JiraStatusDTO] = None
    priority: Optional[JiraPriorityDTO] = None
    issuetype: Optional[JiraIssueTypeDTO] = None


class LinkedIssueDTO(BaseModel):
    """DTO for a linked issue"""
    id: str
    key: str
    self_url: str = Field(alias="self")
    fields: LinkedIssueFieldsDTO


class IssueLinkTypeDTO(BaseModel):
    """DTO for issue link type"""
    id: str
    name: str
    inward: str
    outward: str
    self_url: str = Field(alias="self")


class JiraIssueLinkDTO(BaseModel):
    """DTO for a Jira issue link"""
    id: str
    self_url: str = Field(alias="self")
    type: IssueLinkTypeDTO
    inward_issue: Optional[LinkedIssueDTO] = Field(default=None, alias="inwardIssue")
    outward_issue: Optional[LinkedIssueDTO] = Field(default=None, alias="outwardIssue")


class JiraIssueLinksResponseDTO(BaseModel):
    """DTO for response containing issue links"""
    issue_links: List[JiraIssueLinkDTO] = Field(alias="issuelinks", default_factory=list)
