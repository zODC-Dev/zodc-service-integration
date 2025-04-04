from typing import Any, Dict

from src.configs.logger import log
from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO
from src.domain.models.jira_user import JiraUserModel


class JiraUserMapper:
    """Mapper for Jira user API responses to domain models"""

    @staticmethod
    def to_domain(api_response: JiraUserAPIGetResponseDTO) -> JiraUserModel:
        """Convert API response DTO to domain model"""
        try:
            # Extract avatar URL if available
            avatar_url = ""
            if api_response.avatar_urls and isinstance(api_response.avatar_urls, dict):
                avatar_url = api_response.avatar_urls.get("48x48", "")

            return JiraUserModel(
                jira_account_id=api_response.account_id,
                name=api_response.display_name,
                email=api_response.email_address or "",
                is_active=api_response.active,
                avatar_url=avatar_url
            )
        except Exception as e:
            log.error(f"Error mapping user API response to domain model: {str(e)}")
            # Return minimal valid model to prevent sync failure
            return JiraUserModel(
                jira_account_id=api_response.account_id,
                name=api_response.display_name or "Unknown User",
                is_active=getattr(api_response, 'active', True)
            )

    @staticmethod
    def from_domain(model: JiraUserModel) -> Dict[str, Any]:
        """Convert domain model to API request format"""
        try:
            return {
                "accountId": model.jira_account_id,
                "name": model.name,
                "emailAddress": model.email,
                "active": model.is_active
            }
        except Exception as e:
            log.error(f"Error mapping domain model to API request: {str(e)}")
            # Return minimal valid model for API
            return {
                "accountId": model.jira_account_id,
                "name": model.name
            }
