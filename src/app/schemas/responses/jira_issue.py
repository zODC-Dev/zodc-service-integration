from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel

from src.app.schemas.responses.base import BaseResponse
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_issue_comment import JiraIssueCommentModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class JiraAssigneeResponse(BaseResponse):
    id: Optional[int] = None
    jira_account_id: str
    email: str
    avatar_url: Optional[str] = None
    name: str
    is_system_user: bool

    @classmethod
    def from_domain(cls, assignee: JiraUserModel) -> "JiraAssigneeResponse":
        return cls(
            id=assignee.user_id,
            jira_account_id=assignee.jira_account_id,
            email=assignee.email,
            avatar_url=assignee.avatar_url,
            name=assignee.name,
            is_system_user=assignee.is_system_user
        )


class JiraIssuePriorityResponse(BaseModel):
    id: str
    name: str
    icon_url: str


class JiraIssueSprintResponse(BaseModel):
    id: Optional[int] = None
    name: str
    state: str

    @classmethod
    def from_domain(cls, sprint: JiraSprintModel) -> "JiraIssueSprintResponse":
        return cls(
            id=sprint.jira_sprint_id,
            name=sprint.name,
            state=sprint.state,
        )


class GetJiraIssueResponse(BaseResponse):
    id: Optional[int] = None
    key: str
    summary: str
    assignee: Optional[JiraAssigneeResponse] = None
    reporter: Optional[JiraAssigneeResponse] = None
    priority: Optional[str] = None
    type: JiraIssueType
    sprint: Optional[JiraIssueSprintResponse] = None
    estimate_point: float = 0
    actual_point: Optional[float] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: JiraIssueStatus
    is_system_linked: bool = False
    is_deleted: bool = False
    link_url: Optional[str] = None
    last_synced_at: datetime

    @classmethod
    def from_domain(cls, issue: JiraIssueModel, sprint: Optional[JiraSprintModel] = None) -> "GetJiraIssueResponse":

        current_sprint: Optional[JiraIssueSprintResponse] = None
        if sprint:
            current_sprint = JiraIssueSprintResponse.from_domain(sprint)

        return cls(
            id=issue.id,
            key=issue.key,
            summary=issue.summary,
            assignee=JiraAssigneeResponse.from_domain(issue.assignee) if issue.assignee else None,
            priority=issue.priority,
            type=issue.type,
            sprint=current_sprint,
            status=issue.status,
            estimate_point=issue.estimate_point,
            actual_point=issue.actual_point,
            description=issue.description,
            created_at=issue.created_at,
            is_system_linked=issue.is_system_linked,
            is_deleted=issue.is_deleted,
            link_url=issue.link_url,
            last_synced_at=issue.last_synced_at,
            reporter=JiraAssigneeResponse.from_domain(issue.reporter) if issue.reporter else None
        )


class JiraCreateIssueResponse(BaseResponse):
    id: str
    key: str
    self: str  # API URL of the created issue


class JiraIssueDescriptionAPIGetDTO(BaseModel):
    """Response model for Jira issue description"""
    key: str
    description: Optional[str] = None


class JiraIssueCommentAPIGetDTO(BaseModel):
    """Response model for Jira issue comments"""
    id: str
    assignee: JiraAssigneeResponse
    content: str
    created_at: datetime

    class Config:
        populate_by_name = True
        alias_generator = to_camel

    @classmethod
    def from_domain(cls, comment: JiraIssueCommentModel) -> "JiraIssueCommentAPIGetDTO":
        return cls(
            id=comment.id,
            assignee=JiraAssigneeResponse.from_domain(comment.assignee),
            content=comment.content,
            created_at=comment.created_at
        )


class JiraIssueCommentAPICreateDTO(BaseModel):
    """Request model for creating a Jira issue comment"""
    content: str
