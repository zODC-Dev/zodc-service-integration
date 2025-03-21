from datetime import datetime, timezone

from src.configs.logger import log
from src.domain.models.jira_project import JiraProjectModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.infrastructure.dtos.jira.project_responses import JiraAPIProjectResponse
from src.infrastructure.dtos.jira.sprint_responses import JiraAPISprintResponse
from src.infrastructure.dtos.jira.user_responses import JiraAPIUserResponse


class JiraProjectMapper:
    @staticmethod
    def to_domain(api_response: JiraAPIProjectResponse) -> JiraProjectModel:
        return JiraProjectModel(
            project_id=api_response.id,
            key=api_response.key,
            name=api_response.name,
            jira_project_id=api_response.id,
            avatar_url=api_response.avatarUrls.get("48x48", "")
        )


class JiraUserMapper:
    @staticmethod
    def to_domain(api_response: JiraAPIUserResponse) -> JiraUserModel:
        return JiraUserModel(
            jira_account_id=api_response.accountId,
            email=api_response.emailAddress,
            name=api_response.displayName,
            is_active=api_response.active,
            avatar_url=api_response.avatarUrls.get("48x48", "")
        )


class JiraSprintMapper:
    @staticmethod
    def to_domain(api_response: JiraAPISprintResponse) -> JiraSprintModel:
        try:
            now = datetime.now(timezone.utc)
            return JiraSprintModel(
                jira_sprint_id=api_response.id,
                name=api_response.name,
                state=api_response.state,
                start_date=api_response.startDate and api_response.startDate.replace(tzinfo=timezone.utc),
                end_date=api_response.endDate and api_response.endDate.replace(tzinfo=timezone.utc),
                complete_date=api_response.completeDate and api_response.completeDate.replace(tzinfo=timezone.utc),
                goal=api_response.goal,
                created_at=now
            )
        except Exception as e:
            log.error(f"Error mapping sprint response to domain: {str(e)}")
            return JiraSprintModel(
                jira_sprint_id=api_response.id,
                name=api_response.name,
                state=api_response.state,
                created_at=datetime.now(timezone.utc)
            )
