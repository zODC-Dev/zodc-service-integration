from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.app.schemas.responses.base import BaseResponse
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class JiraAssigneeResponse(BaseModel):
    id: Optional[int] = None
    jira_account_id: str
    email: str
    avatar_url: Optional[str] = None
    name: str
    is_system_user: bool

    @classmethod
    def from_domain(cls, assignee: JiraUserModel) -> "JiraAssigneeResponse":
        return cls(
            id=assignee.id,
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
    priority: Optional[JiraIssuePriorityResponse] = None
    type: JiraIssueType
    sprint: Optional[JiraIssueSprintResponse] = None
    estimate_point: float = 0
    actual_point: Optional[float] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: JiraIssueStatus
    is_system_linked: bool = False

    @classmethod
    def from_domain(cls, issue: JiraIssueModel, sprint_number: Optional[int] = None) -> "GetJiraIssueResponse":

        current_sprint: Optional[JiraIssueSprintResponse] = None
        if issue.sprints:
            current_sprint = JiraIssueSprintResponse.from_domain(
                next((sprint for sprint in issue.sprints if (
                    sprint and sprint.jira_sprint_id == sprint_number)), None)
            )

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
            is_system_linked=issue.is_system_linked
        )


class JiraCreateIssueResponse(BaseResponse):
    id: str
    key: str
    self: str  # API URL of the created issue
