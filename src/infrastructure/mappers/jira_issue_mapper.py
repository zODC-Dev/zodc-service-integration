from datetime import datetime, timezone
from typing import Optional

from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira_issue import JiraIssueModel, JiraIssuePriorityModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.infrastructure.dtos.jira.common import JiraAPIIssuePriorityResponse
from src.infrastructure.dtos.jira.issue_responses import JiraAPIIssueResponse
from src.infrastructure.dtos.jira.sprint_responses import JiraAPISprintResponse
from src.infrastructure.dtos.jira.user_responses import JiraAPIUserResponse


class JiraIssueMapper:
    @staticmethod
    def _map_user(user_response: JiraAPIUserResponse) -> Optional[JiraUserModel]:
        if not user_response:
            return None
        try:
            avatar_url = ""
            if isinstance(user_response.avatarUrls, dict):
                avatar_url = user_response.avatarUrls.get("48x48", "")

            return JiraUserModel(
                jira_account_id=user_response.accountId,
                email=getattr(user_response, 'emailAddress', '') or '',
                name=user_response.displayName,
                avatar_url=avatar_url,
                is_system_user=False
            )
        except Exception as e:
            log.error(f"Error mapping user response to domain: {str(e)}")
            # Return minimal valid model
            return JiraUserModel(
                jira_account_id=user_response.accountId,
                email='',
                name=user_response.displayName or '',
                avatar_url='',
                is_system_user=False
            )

    @staticmethod
    def to_domain_issue(api_response: JiraAPIIssueResponse) -> JiraIssueModel:
        log.info(f"Mapping issue response to domain: {api_response}")
        try:
            fields = api_response.fields
            now = datetime.now(timezone.utc)

            # Get sprint data and use jira_sprint_id directly
            sprint = None
            sprint_id = None
            if fields.customfield_10020 and len(fields.customfield_10020) > 0:
                jira_sprint = fields.customfield_10020[0]
                sprint = JiraIssueMapper._map_sprint(jira_sprint)
                sprint_id = jira_sprint.id  # Use Jira's sprint ID directly

            return JiraIssueModel(
                key=api_response.key,
                summary=fields.summary,
                description=fields.description or "",
                status=JiraIssueStatus(fields.status.name),
                assignee=JiraIssueMapper._map_user(fields.assignee) if fields.assignee else None,
                priority=JiraIssueMapper._map_priority(fields.priority) if fields.priority else None,
                type=JiraIssueType(fields.issuetype.name),
                sprint=sprint,
                sprint_id=sprint_id,  # Use Jira's sprint ID directly
                estimate_point=fields.customfield_10016 or 0,
                actual_point=fields.customfield_10017,
                created_at=fields.created.replace(tzinfo=timezone.utc) if fields.created else now,
                updated_at=fields.updated.replace(tzinfo=timezone.utc) if fields.updated else now,
                jira_issue_id=api_response.id,
                project_key=api_response.key.split("-")[0],
                reporter_id=getattr(fields.reporter, 'accountId', None) if hasattr(fields, 'reporter') else None,
                last_synced_at=now
            )
        except Exception as e:
            log.error(f"Error mapping issue response to domain: {str(e)}")
            # Return minimal valid model
            now = datetime.now(timezone.utc)
            return JiraIssueModel(
                key=api_response.key,
                summary=getattr(api_response.fields, 'summary', 'No summary'),
                description='',
                status=JiraIssueStatus.TO_DO,
                type=JiraIssueType.TASK,
                estimate_point=0,
                jira_issue_id=api_response.id,
                project_key=api_response.key.split("-")[0],
                created_at=now,
                updated_at=now,
                last_synced_at=now,
                sprint_id=None
            )

    @staticmethod
    def _map_priority(api_priority: JiraAPIIssuePriorityResponse) -> JiraIssuePriorityModel:
        return JiraIssuePriorityModel(
            id=api_priority.id,
            name=api_priority.name,
            icon_url=api_priority.icon_url
        )

    @staticmethod
    def _map_sprint(api_sprint: JiraAPISprintResponse) -> Optional[JiraSprintModel]:
        try:
            now = datetime.now(timezone.utc)
            return JiraSprintModel(
                jira_sprint_id=api_sprint.id,
                name=api_sprint.name,
                state=api_sprint.state,
                start_date=api_sprint.startDate and api_sprint.startDate.replace(tzinfo=timezone.utc),
                end_date=api_sprint.endDate and api_sprint.endDate.replace(tzinfo=timezone.utc),
                complete_date=api_sprint.completeDate and api_sprint.completeDate.replace(tzinfo=timezone.utc),
                goal=api_sprint.goal,
                created_at=now
            )
        except Exception as e:
            log.error(f"Error mapping sprint: {str(e)}")
            return None

    # Add other mapping methods as needed
