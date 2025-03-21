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
from src.infrastructure.entities.jira_issue import JiraIssueEntity


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
        try:
            fields = api_response.fields
            now = datetime.now(timezone.utc)

            # Map all sprints from the customfield
            sprints = []
            if fields.customfield_10020:
                for jira_sprint in fields.customfield_10020:
                    sprint = JiraIssueMapper._map_sprint(jira_sprint)
                    if sprint:
                        sprints.append(sprint)

            # Get reporter_id and assignee_id safely
            reporter_id = None
            try:
                if hasattr(fields, 'reporter') and fields.reporter:
                    reporter_id = getattr(fields.reporter, 'accountId', None)
            except AttributeError:
                log.warning(f"No reporter found for issue {api_response.key}")

            # Get assignee safely
            assignee = None
            assignee_id = None
            try:
                if hasattr(fields, 'assignee') and fields.assignee:
                    assignee_id = getattr(fields.assignee, 'accountId', None)
                    if assignee_id:
                        assignee = JiraIssueMapper._map_user(fields.assignee)
            except AttributeError:
                log.warning(f"No assignee found for issue {api_response.key}")

            return JiraIssueModel(
                key=api_response.key,
                summary=fields.summary,
                description=fields.description or "",
                status=JiraIssueStatus(fields.status.name),
                assignee=assignee,
                assignee_id=assignee_id,
                priority=JiraIssueMapper._map_priority(fields.priority) if fields.priority else None,
                type=JiraIssueType(fields.issuetype.name),
                sprints=sprints,
                estimate_point=fields.customfield_10016 or 0,
                actual_point=fields.customfield_10017,
                created_at=fields.created.replace(tzinfo=timezone.utc) if fields.created else now,
                updated_at=fields.updated.replace(tzinfo=timezone.utc) if fields.updated else now,
                jira_issue_id=api_response.id,
                project_key=api_response.key.split("-")[0],
                reporter_id=reporter_id,
                last_synced_at=now
            )
        except Exception as e:
            log.error(f"Error mapping issue response to domain: {str(e)}")
            # Return minimal valid model with None for user IDs
            now = datetime.now(timezone.utc)
            return JiraIssueModel(
                key=api_response.key,
                summary=getattr(api_response.fields, 'summary', 'No summary'),
                description='',
                status=JiraIssueStatus.TO_DO,
                type=JiraIssueType.TASK,
                estimate_point=0,
                sprints=[],
                jira_issue_id=api_response.id,
                project_key=api_response.key.split("-")[0],
                created_at=now,
                updated_at=now,
                last_synced_at=now,
                reporter_id=None,
                assignee_id=None,
                assignee=None
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
                created_at=now,
            )
        except Exception as e:
            log.error(f"Error mapping sprint: {str(e)}")
            return None

    @staticmethod
    def to_entity(model: JiraIssueModel) -> JiraIssueEntity:
        return JiraIssueEntity(
            jira_issue_id=model.jira_issue_id,
            key=model.key,
            summary=model.summary,
            description=model.description,
            status=model.status.value,
            type=model.type.value,
            priority_id=model.priority.id if model.priority else None,
            estimate_point=model.estimate_point,
            actual_point=model.actual_point,
            project_key=model.project_key,
            reporter_id=model.reporter_id,  # Ensure reporter_id is passed
            assignee_id=model.assignee_id,  # Use assignee_id directly
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_synced_at=model.last_synced_at,
            updated_locally=model.updated_locally,
            sprints=[]
        )

    @staticmethod
    def to_domain(entity: JiraIssueEntity) -> JiraIssueModel:
        sprints = []
        for issue_sprint in entity.sprints:
            sprint = JiraSprintModel(
                jira_sprint_id=issue_sprint.jira_sprint_id,
                name=issue_sprint.name,
                state=issue_sprint.state,
                start_date=issue_sprint.start_date,
                end_date=issue_sprint.end_date,
                complete_date=issue_sprint.complete_date,
                goal=issue_sprint.goal,
                created_at=issue_sprint.created_at,
                updated_at=issue_sprint.updated_at,
                project_key=issue_sprint.project_key
            )
            sprints.append(sprint)

        return JiraIssueModel(
            id=entity.id,
            key=entity.key,
            summary=entity.summary,
            description=entity.description,
            status=JiraIssueStatus(entity.status),
            type=JiraIssueType(entity.type),
            priority=None,  # Will be set by repository if needed
            estimate_point=entity.estimate_point,
            actual_point=entity.actual_point,
            project_key=entity.project_key,
            reporter_id=entity.reporter_id,
            assignee=None,  # Will be set by repository if needed
            sprints=sprints,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_synced_at=entity.last_synced_at,
            jira_issue_id=entity.jira_issue_id,
            updated_locally=entity.updated_locally
        )

    # Add other mapping methods as needed
