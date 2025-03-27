from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, field_serializer, model_validator

from src.configs.logger import log


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
    board_id: Optional[int] = Field(default=None, alias="boardId")
    goal: Optional[str] = None
    start_date: Optional[datetime] = Field(default=None, alias="startDate")
    end_date: Optional[datetime] = Field(default=None, alias="endDate")
    complete_date: Optional[datetime] = Field(default=None, alias="completeDate")
    origin_board_id: Optional[str] = Field(default=None, alias="originBoardId")

    @field_serializer('start_date')
    def serialize_start_date(self, value: Optional[datetime], _info):
        if value is None:
            return None
        return value.isoformat()

    @field_serializer('end_date')
    def serialize_end_date(self, value: Optional[datetime], _info):
        if value is None:
            return None
        return value.isoformat()

    @field_serializer('complete_date')
    def serialize_complete_date(self, value: Optional[datetime], _info):
        if value is None:
            return None
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
    sprints: Optional[List[JiraSprint | None]] = Field(default=None, alias="customfield_10020")


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


class BaseJiraWebhookDTO(BaseModel):
    """Base class for all Jira webhook DTOs"""
    timestamp: int
    webhook_event: str = Field(alias="webhookEvent")
    normalized_event: Optional[str] = None

    # Static registry của các loại webhook
    webhook_registry: ClassVar[Dict[str, Type["BaseJiraWebhookDTO"]]] = {}

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """Đăng ký tự động các lớp con"""
        super().__init_subclass__(**kwargs)
        # Lấy tên webhook_event mà lớp này xử lý từ các event_types của lớp con
        if hasattr(cls, "event_types") and cls.event_types:
            for event_type in cls.event_types:
                BaseJiraWebhookDTO.webhook_registry[event_type] = cls

    @model_validator(mode='after')
    def normalize_event(self):
        """Chuẩn hóa tên event"""
        # Chỉ chuẩn hóa nếu normalized_event chưa được thiết lập
        if self.normalized_event is None:
            # Chuẩn hóa event name
            if not self.webhook_event.startswith("jira:") and not self.webhook_event.startswith("sprint_"):
                self.normalized_event = f"jira:{self.webhook_event}"
            else:
                # Các điều kiện đặc biệt
                if self.webhook_event == "sprint_created":
                    self.normalized_event = "jira:sprint_created"
                elif self.webhook_event == "sprint_updated":
                    self.normalized_event = "jira:sprint_updated"
                elif self.webhook_event == "sprint_started":
                    self.normalized_event = "jira:sprint_started"
                elif self.webhook_event == "sprint_closed":
                    self.normalized_event = "jira:sprint_closed"
                elif self.webhook_event.startswith("sprint_"):
                    # Chuẩn hóa tất cả sự kiện sprint_ khác
                    self.normalized_event = f"jira:{self.webhook_event}"
                else:
                    # Giữ nguyên giá trị nếu đã có định dạng chuẩn
                    self.normalized_event = self.webhook_event

        return self

    @classmethod
    def parse_webhook(cls, data: Dict[str, Any]) -> "BaseJiraWebhookDTO":
        """Factory method để tạo đúng loại DTO dựa trên webhook_event"""
        log.info(f"Parsing webhook data: {data}")
        if not data and ("webhookEvent" not in data or "webhook_event" not in data):
            raise ValueError("Invalid webhook payload: missing webhookEvent field")

        webhook_event = data["webhookEvent"] if "webhookEvent" in data else data["webhook_event"]

        # Chuẩn hóa event name
        normalized_event = webhook_event
        if not webhook_event.startswith("jira:") and not webhook_event.startswith("sprint_"):
            normalized_event = f"jira:{webhook_event}"

        # Các điều kiện đặc biệt
        if webhook_event == "sprint_created":
            normalized_event = "jira:sprint_created"
        elif webhook_event == "sprint_updated":
            normalized_event = "jira:sprint_updated"
        elif webhook_event == "sprint_started":
            normalized_event = "jira:sprint_started"
        elif webhook_event == "sprint_closed":
            normalized_event = "jira:sprint_closed"

        # Tìm DTO phù hợp
        dto_class = cls.webhook_registry.get(normalized_event)

        if dto_class:
            try:
                dto = dto_class.model_validate(data)
                # Thiết lập normalized_event
                dto.normalized_event = normalized_event
                return dto
            except Exception as e:
                # Thử dùng exclude_unset để bỏ qua các trường không có trong payload
                try:
                    dto = dto_class.model_validate(data)
                    dto.normalized_event = normalized_event
                    return dto
                except Exception as nested_e:
                    raise ValueError(f"Failed to parse {webhook_event} webhook: {str(e)}") from nested_e
        else:
            # Fallback về base class nếu không có specific handler
            dto = cls.model_validate(data)
            dto.normalized_event = normalized_event
            return dto

    def to_json_serializable(self) -> Dict[str, Any]:
        """Convert payload to JSON serializable format"""
        return self.model_dump(by_alias=True, mode="json")


class JiraIssueWebhookDTO(BaseJiraWebhookDTO):
    """DTO for issue-related webhooks"""
    event_types: ClassVar[List[str]] = ["jira:issue_created", "jira:issue_updated", "jira:issue_deleted"]

    user: JiraUser
    issue: JiraIssue
    changelog: Optional[JiraChangelog] = None
    issue_event_type_name: Optional[str] = Field(default=None, alias="issue_event_type_name")


class JiraSprintWebhookDTO(BaseJiraWebhookDTO):
    """DTO for sprint-related webhooks"""
    event_types: ClassVar[List[str]] = ["jira:sprint_created", "jira:sprint_updated", "jira:sprint_started", "jira:sprint_closed",
                                        "sprint_created", "sprint_updated", "sprint_started", "sprint_closed"]

    sprint: JiraSprint
    user: Optional[JiraUser] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_sprint_fields(cls, values):
        """Normalize sprint fields for better compatibility"""
        if isinstance(values, dict) and "sprint" in values and values["sprint"]:
            sprint = values["sprint"]
            # Map fields consistently
            if "originBoardId" in sprint and isinstance(sprint["originBoardId"], (int, str)):
                # Ensure we handle both string and int forms of originBoardId
                sprint["originBoardId"] = str(sprint["originBoardId"])

            # Handle dates with timezone info
            for date_field in ["startDate", "endDate", "completeDate", "createdDate"]:
                if date_field in sprint and sprint[date_field] and isinstance(sprint[date_field], str):
                    # Ensure datetime fields are parsed correctly with timezone
                    pass  # Pydantic should handle ISO format conversions

        return values


# Backward compatibility for existing code
JiraWebhookResponseDTO = Union[JiraIssueWebhookDTO, JiraSprintWebhookDTO, BaseJiraWebhookDTO]
