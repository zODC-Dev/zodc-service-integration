from datetime import datetime, timezone
from typing import List, Optional

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.jira import JiraIssueStatus, JiraIssueType
from src.domain.models.jira.apis.responses.common import JiraAPIIssuePriorityResponse
from src.domain.models.jira.apis.responses.jira_issue import JiraIssueAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_sprint import JiraSprintAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_issue import JiraIssueModel, JiraIssuePriorityModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.infrastructure.entities.jira_issue import JiraIssueEntity


class JiraIssueMapper:
    @staticmethod
    def _map_user(user_response: JiraUserAPIGetResponseDTO) -> Optional[JiraUserModel]:
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
    def to_domain_issue(api_response: JiraIssueAPIGetResponseDTO) -> JiraIssueModel:
        try:
            fields = api_response.fields
            now = datetime.now(timezone.utc)

            # Đảm bảo truy cập các field từ fields object
            summary = fields.summary if hasattr(fields, 'summary') else ""
            description = fields.description if hasattr(fields, 'description') else None

            # Map user data
            assignee = None
            assignee_id = None
            reporter_id = None

            if hasattr(fields, 'assignee') and fields.assignee:
                assignee_id = fields.assignee.accountId
                assignee = JiraIssueMapper._map_user(fields.assignee)

            if hasattr(fields, 'reporter') and fields.reporter:
                reporter_id = fields.reporter.accountId

            # Map sprints
            sprints = []
            if hasattr(fields, 'customfield_10020') and fields.customfield_10020:
                sprints = JiraIssueMapper._map_sprints(fields.customfield_10020)

            # Create link URL
            jira_base_url = settings.JIRA_DASHBOARD_URL
            project_key = api_response.key.split("-")[0]
            current_sprint_id = sprints[0].board_id if sprints else 3
            link_url = f"{jira_base_url}/jira/software/projects/{project_key}/boards/{current_sprint_id}?selectedIssue={api_response.key}"

            return JiraIssueModel(
                jira_issue_id=api_response.id,
                key=api_response.key,
                project_key=project_key,
                summary=summary,
                description=description,
                type=JiraIssueType(fields.issuetype.name) if hasattr(fields, 'issuetype') else JiraIssueType.TASK,
                status=JiraIssueStatus(fields.status.name) if hasattr(fields, 'status') else JiraIssueStatus.TO_DO,
                assignee_id=assignee_id,
                reporter_id=reporter_id,
                estimate_point=getattr(fields, 'customfield_10016', None),
                actual_point=getattr(fields, 'customfield_10017', None),
                created_at=JiraIssueMapper._parse_datetime(fields.created) if hasattr(fields, 'created') else now,
                updated_at=JiraIssueMapper._parse_datetime(fields.updated) if hasattr(fields, 'updated') else now,
                sprints=sprints,
                link_url=link_url,
                assignee=assignee
            )
        except Exception as e:
            log.error(f"Error mapping API response to domain issue: {str(e)}")
            raise

    @staticmethod
    def _map_priority(api_priority: JiraAPIIssuePriorityResponse) -> JiraIssuePriorityModel:
        return JiraIssuePriorityModel(
            id=api_priority.id,
            name=api_priority.name,
            icon_url=api_priority.icon_url
        )

    @staticmethod
    def _map_sprint(api_sprint: JiraSprintAPIGetResponseDTO) -> Optional[JiraSprintModel]:
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
    def _map_sprints(api_sprints: List[JiraSprintAPIGetResponseDTO]) -> List[JiraSprintModel]:
        if not api_sprints:
            return []
        return [JiraIssueMapper._map_sprint(sprint) for sprint in api_sprints if sprint]

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
            link_url=model.link_url,
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

    # Add other mapping methods as needed
