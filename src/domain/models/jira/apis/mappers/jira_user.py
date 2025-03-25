from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_user import JiraUserModel


class JiraUserMapper:
    @staticmethod
    def to_domain(api_response: JiraUserAPIGetResponseDTO) -> JiraUserModel:
        return JiraUserModel(
            jira_account_id=api_response.accountId,
            email=api_response.emailAddress,
            name=api_response.displayName,
            avatar_url=api_response.avatarUrls.get("48x48", "")
        )
