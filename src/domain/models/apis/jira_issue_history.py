from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel

from src.domain.constants.jira import JiraIssueFieldId
from src.domain.models.jira_user import JiraUserModel


class JiraIssueChangelogDataAPIGetDTO(BaseModel):
    """DTO cho dữ liệu changelog của một field"""
    display_value: Optional[str] = None
    value: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class JiraIssueChangelogAuthorAPIGetDTO(BaseModel):
    """DTO cho tác giả của một changelog"""
    id: Optional[int] = None
    jira_account_id: str
    email: str
    avatar_url: Optional[str] = None
    name: str
    is_system_user: bool

    @classmethod
    def from_domain(cls, assignee: JiraUserModel) -> "JiraIssueChangelogAuthorAPIGetDTO":
        return cls(
            id=assignee.user_id,
            jira_account_id=assignee.jira_account_id,
            email=assignee.email,
            avatar_url=assignee.avatar_url,
            name=assignee.name,
            is_system_user=assignee.is_system_user
        )

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class JiraIssueChangelogAPIGetDTO(BaseModel):
    """DTO cho một changelog của Jira Issue"""
    field_id: JiraIssueFieldId
    created_at: str
    author: JiraIssueChangelogAuthorAPIGetDTO
    from_: Optional[JiraIssueChangelogDataAPIGetDTO] = Field(alias="from", default=None)
    to: Optional[JiraIssueChangelogDataAPIGetDTO] = Field(default=None)

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class JiraIssueHistoryAPIGetDTO(BaseModel):
    """DTO cho lịch sử thay đổi của một Jira Issue"""
    key: str
    created_at: str
    changelogs: List[JiraIssueChangelogAPIGetDTO]

    class Config:
        populate_by_name = True
        alias_generator = to_camel
