from datetime import datetime, timezone
from typing import List, Optional

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

            # Map user data
            assignee = None
            assignee_id = None
            reporter_id = None

            if fields.assignee:
                assignee_id = fields.assignee.accountId
                assignee = JiraIssueMapper._map_user(fields.assignee)

            if fields.reporter:
                reporter_id = fields.reporter.accountId

            # Map sprints
            sprints = []
            if hasattr(fields, 'customfield_10020') and fields.customfield_10020:
                sprints = JiraIssueMapper._map_sprints(fields.customfield_10020)

            # Create link URL
            jira_base_url = JiraIssueMapper._extract_jira_base_url(api_response)
            link_url = f"{jira_base_url}/browse/{api_response.key}" if jira_base_url else None

            return JiraIssueModel(
                key=api_response.key,
                summary=fields.summary,
                description=fields.description or "",
                status=JiraIssueStatus(fields.status.name),
                assignee=assignee,  # Use mapped assignee
                assignee_id=assignee_id,  # Use assignee_id from mapped assignee
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
                last_synced_at=now,
                is_deleted=False,
                link_url=link_url
            )
        except Exception as e:
            log.error(f"Error mapping issue response to domain for issue {api_response.key}: {str(e)}")
            # Return minimal valid model
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
                assignee=None,
                is_deleted=False,
                link_url=None
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
    def _map_sprints(api_sprints: List[JiraAPISprintResponse]) -> List[JiraSprintModel]:
        if not api_sprints:
            return []
        return [JiraIssueMapper._map_sprint(sprint) for sprint in api_sprints]

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
            sprints=[
                JiraSprintModel(
                    jira_sprint_id=sprint.jira_sprint_id,
                    name=sprint.name,
                    state=sprint.state,
                    start_date=sprint.start_date,
                    end_date=sprint.end_date,
                    complete_date=sprint.complete_date,
                    goal=sprint.goal,
                    created_at=sprint.created_at,
                    updated_at=sprint.updated_at,
                    project_key=sprint.project_key
                ) for sprint in entity.sprints
            ],
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_synced_at=entity.last_synced_at,
            jira_issue_id=entity.jira_issue_id,
            updated_locally=entity.updated_locally
        )

    @staticmethod
    def _extract_jira_base_url(api_response: JiraAPIIssueResponse) -> Optional[str]:
        """Extract Jira base URL from API response"""
        if hasattr(api_response, 'self') and api_response.self:
            try:
                parts = api_response.self.split('/rest/api')
                if parts and len(parts) > 0:
                    return parts[0]
            except Exception as e:
                log.warning(f"Could not extract Jira base URL: {str(e)}")
        return None

    # Add other mapping methods as needed
