from src.configs.logger import log
from src.domain.models.jira.apis.responses.jira_project import JiraProjectAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_sprint import JiraSprintAPIGetResponseDTO
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_project import JiraProjectModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel


class JiraProjectMapper:
    @staticmethod
    def to_domain(api_response: JiraProjectAPIGetResponseDTO) -> JiraProjectModel:
        try:
            avatar_url = ""
            if isinstance(api_response.avatarUrls, dict):
                avatar_url = api_response.avatarUrls.get("48x48", "")

            return JiraProjectModel(
                jira_project_id=api_response.id,    # ID từ Jira API
                key=api_response.key,
                name=api_response.name,
                description=api_response.description or "",
                avatar_url=avatar_url
            )
        except Exception as e:
            log.error(f"Error mapping project response to domain: {str(e)}")
            # Return minimal valid model to prevent sync failure
            return JiraProjectModel(
                jira_project_id=api_response.id,
                key=api_response.key,
                name=api_response.name
            )

    @staticmethod
    def to_domain_sprint(api_response: JiraSprintAPIGetResponseDTO) -> JiraSprintModel:
        try:
            return JiraSprintModel(
                jira_sprint_id=api_response.id,
                name=api_response.name,
                state=api_response.state,
                start_date=api_response.startDate,
                end_date=api_response.endDate,
                goal=api_response.goal
            )
        except Exception as e:
            log.error(f"Error mapping sprint response to domain: {str(e)}")
            return JiraSprintModel(
                jira_sprint_id=api_response.id,
                name=api_response.name,
                state=api_response.state
            )

    @staticmethod
    def to_domain_user(api_response: JiraUserAPIGetResponseDTO) -> JiraUserModel:
        avatar_url = ""
        try:
            if isinstance(api_response.avatarUrls, dict):
                avatar_url = api_response.avatarUrls.get("48x48", "")

            return JiraUserModel(
                jira_account_id=api_response.accountId,
                email=api_response.emailAddress or "",
                name=api_response.displayName,
                avatar_url=avatar_url,
                is_system_user=False
            )
        except Exception as e:
            log.error(f"Error mapping user response to domain: {str(e)}")
            # Return minimal valid model
            return JiraUserModel(
                jira_account_id=api_response.accountId,
                email=api_response.emailAddress or "",
                name=api_response.displayName,
                avatar_url=avatar_url,
                is_system_user=False
            )

    @staticmethod
    def to_domain_project(api_response: JiraProjectAPIGetResponseDTO) -> JiraProjectModel:
        return JiraProjectModel(
            jira_project_id=api_response.id,
            key=api_response.key,
            name=api_response.name,
            description=api_response.description or "",
            avatar_url=api_response.avatarUrls.get("48x48", ""),
            user_id=None
        )
