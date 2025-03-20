from datetime import datetime

from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel, JiraIssuePriorityModel
from src.domain.models.jira_project import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.infrastructure.dtos.jira.common import JiraAPISprintResponse, JiraAPIUserResponse
from src.infrastructure.dtos.jira.issue_responses import JiraAPIIssuePriorityResponse, JiraAPIIssueResponse


class JiraIssueMapper:
    @staticmethod
    def to_domain_issue(api_response: JiraAPIIssueResponse) -> JiraIssueModel:
        fields = api_response.fields
        return JiraIssueModel(
            jira_id=api_response.id,
            key=api_response.key,
            summary=fields.summary,
            description=fields.description,
            status=JiraIssueStatus(fields.status.name),
            assignee=JiraIssueMapper._map_user(fields.assignee) if fields.assignee else None,
            priority=JiraIssueMapper._map_priority(fields.priority) if fields.priority else None,
            type=JiraIssueType(fields.issuetype.name),
            sprint=JiraIssueMapper._map_sprint(fields.customfield_10020[0]) if fields.customfield_10020 else None,
            estimate_point=fields.customfield_10016 or 0,
            actual_point=fields.customfield_10017,
            created_at=fields.created,
            updated_at=fields.updated,
            jira_issue_id=api_response.id,
            project_key=api_response.key.split("-")[0],
            reporter_id=None,
            last_synced_at=datetime.utcnow()
        )

    @staticmethod
    def _map_user(api_user: JiraAPIUserResponse) -> JiraUserModel:
        return JiraUserModel(
            account_id=api_user.account_id,
            email_address=api_user.email_address,
            display_name=api_user.display_name,
            email=api_user.email_address or "",
            user_id=None  # Will be set later
        )

    @staticmethod
    def _map_priority(api_priority: JiraAPIIssuePriorityResponse) -> JiraIssuePriorityModel:
        return JiraIssuePriorityModel(
            id=api_priority.id,
            name=api_priority.name,
            icon_url=api_priority.icon_url
        )

    @staticmethod
    def _map_sprint(api_sprint: JiraAPISprintResponse) -> JiraSprintModel:
        return JiraSprintModel(
            id=api_sprint.id,
            name=api_sprint.name,
            state=api_sprint.state,
            start_date=api_sprint.start_date,
            end_date=api_sprint.end_date,
            goal=api_sprint.goal
        )

    # Add other mapping methods as needed
