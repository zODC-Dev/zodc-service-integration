from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_serializer


class JiraAvatarUrls(BaseModel):
    """Avatar URLs for Jira user"""
    x48: str = Field(alias="48x48")
    x24: str = Field(alias="24x24")
    x16: str = Field(alias="16x16")
    x32: str = Field(alias="32x32")


class JiraUser(BaseModel):
    """Jira user information"""
    self: str
    account_id: str = Field(alias="accountId")
    avatar_urls: JiraAvatarUrls = Field(alias="avatarUrls")
    display_name: str = Field(alias="displayName")
    active: bool
    time_zone: str = Field(alias="timeZone")
    account_type: str = Field(alias="accountType")


class JiraIssueType(BaseModel):
    """Issue type information"""
    self: str
    id: str
    description: str
    icon_url: str = Field(alias="iconUrl")
    name: str
    subtask: bool
    avatar_id: int = Field(alias="avatarId")
    entity_id: str = Field(alias="entityId")
    hierarchy_level: int = Field(alias="hierarchyLevel")


class JiraProject(BaseModel):
    """Project information"""
    self: str
    id: str
    key: str
    name: str
    project_type_key: str = Field(alias="projectTypeKey")
    simplified: bool
    avatar_urls: JiraAvatarUrls = Field(alias="avatarUrls")


class JiraStatusCategory(BaseModel):
    """Status category information"""
    self: str
    id: int
    key: str
    color_name: str = Field(alias="colorName")
    name: str


class JiraStatus(BaseModel):
    """Issue status information"""
    self: str
    description: str
    icon_url: str = Field(alias="iconUrl")
    name: str
    id: str
    status_category: JiraStatusCategory = Field(alias="statusCategory")


class JiraSprint(BaseModel):
    """Sprint information"""
    id: int
    name: str
    state: str
    board_id: int = Field(alias="boardId")
    goal: str
    start_date: datetime = Field(alias="startDate")
    end_date: datetime = Field(alias="endDate")

    @field_serializer('start_date')
    def serialize_start_date(self, value: datetime, _info):
        return value.isoformat()

    @field_serializer('end_date')
    def serialize_end_date(self, value: datetime, _info):
        return value.isoformat()


class JiraPriority(BaseModel):
    """Priority information"""
    self: str
    icon_url: str = Field(alias="iconUrl")
    name: str
    id: str


class JiraIssueFields(BaseModel):
    """Issue fields"""
    status_category_change_date: str = Field(alias="statuscategorychangedate")
    issue_type: JiraIssueType = Field(alias="issuetype")
    project: JiraProject
    created: str
    updated: str
    status: JiraStatus
    summary: str
    description: Optional[str] = None
    assignee: Optional[JiraUser] = None
    reporter: Optional[JiraUser] = None
    priority: Optional[JiraPriority] = None
    estimate_point: Optional[float] = Field(default=None, alias="customfield_10016")
    actual_point: Optional[float] = Field(default=None, alias="customfield_10017")
    sprints: Optional[List[JiraSprint]] = Field(default=None, alias="customfield_10020")


class JiraIssue(BaseModel):
    """Issue information"""
    id: str
    self: str
    key: str
    fields: JiraIssueFields


class JiraChangelogItem(BaseModel):
    """Changelog item information"""
    field: str
    fieldtype: str
    field_id: str = Field(alias="fieldId")
    from_: Optional[str] = Field(default=None, alias="from")
    from_string: Optional[str] = Field(default=None, alias="fromString")
    to: Optional[str] = None
    to_string: Optional[str] = Field(default=None, alias="toString")


class JiraChangelog(BaseModel):
    """Changelog information"""
    id: str
    items: List[JiraChangelogItem]


class JiraWebhookPayload(BaseModel):
    """Main webhook payload"""
    timestamp: int
    webhook_event: str = Field(alias="webhookEvent")
    issue_event_type_name: Optional[str] = Field(default=None, alias="issue_event_type_name")
    user: JiraUser
    issue: JiraIssue
    changelog: Optional[JiraChangelog] = None

    @classmethod
    def parse_webhook(cls, data: Dict[str, Any]) -> "JiraWebhookPayload":
        """Parse webhook data into model"""
        try:
            return cls.model_validate(data)
        except Exception as e:
            raise ValueError(f"Invalid webhook payload: {str(e)}") from e

    def to_json_serializable(self) -> Dict[str, Any]:
        """Convert payload to JSON serializable format"""
        # Directly return model_dump since all fields are already JSON serializable
        # The fields.created and fields.updated are already strings from Jira
        return self.model_dump(by_alias=True, mode="json")
