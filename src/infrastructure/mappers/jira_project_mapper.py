from src.domain.models.jira_project import JiraProjectModel, JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.infrastructure.dtos.jira.project_responses import (
    JiraAPIProjectResponse,
    JiraAPIProjectSprintResponse,
    JiraAPIProjectUserResponse,
)


class JiraProjectMapper:
    @staticmethod
    def to_domain_project(api_response: JiraAPIProjectResponse) -> JiraProjectModel:
        return JiraProjectModel(
            id=api_response.id,
            key=api_response.key,
            name=api_response.name,
            description=api_response.description,
            project_type=api_response.project_type_key,
            project_category=api_response.project_category.get("name") if api_response.project_category else None,
            lead=api_response.lead.get("displayName") if api_response.lead else None,
            url=api_response.url,
            avatar_url=api_response.avatar_urls.get("48x48"),
            project_id=0,  # Will be set later
            jira_project_id=api_response.id
        )

    @staticmethod
    def to_domain_sprint(api_response: JiraAPIProjectSprintResponse) -> JiraSprintModel:
        return JiraSprintModel(
            id=api_response.id,
            name=api_response.name,
            state=api_response.state,
            start_date=api_response.start_date,
            end_date=api_response.end_date,
            goal=api_response.goal
        )

    @staticmethod
    def to_domain_user(api_response: JiraAPIProjectUserResponse) -> JiraUserModel:
        return JiraUserModel(
            account_id=api_response.account_id,
            email_address=api_response.email_address,
            display_name=api_response.display_name,
            email=api_response.email_address or "",
            user_id=None  # Will be set later
        )
