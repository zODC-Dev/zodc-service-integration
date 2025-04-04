from datetime import datetime, timezone

from src.configs.logger import log
from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraUserWebhookDTO


class JiraUserWebhookMapper:
    """Mapper for Jira user webhook data to database DTOs"""

    @classmethod
    def map_to_create_dto(cls, webhook_data: JiraUserWebhookDTO) -> JiraUserDBCreateDTO:
        """Map webhook data to JiraUserDBCreateDTO"""
        try:
            user = webhook_data.user

            # Lấy avatar URL nếu có
            avatar_url = ""
            if user.avatar_urls:
                avatar_url = user.avatar_urls.get("48x48", "")

            return JiraUserDBCreateDTO(
                jira_account_id=user.account_id,
                name=user.display_name,
                email=user.email_address or "",
                is_active=user.active,
                avatar_url=avatar_url,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
        except Exception as e:
            log.error(f"Error mapping user webhook data to create DTO: {str(e)}")
            raise

    @classmethod
    def map_to_update_dto(cls, webhook_data: JiraUserWebhookDTO) -> JiraUserDBUpdateDTO:
        """Map webhook data to JiraUserDBUpdateDTO"""
        try:
            user = webhook_data.user

            # Lấy avatar URL nếu có
            avatar_url = ""
            if user.avatar_urls:
                avatar_url = user.avatar_urls.get("48x48", "")

            return JiraUserDBUpdateDTO(
                name=user.display_name,
                email=user.email_address,
                is_active=user.active,
                avatar_url=avatar_url,
                updated_at=datetime.now(timezone.utc)
            )
        except Exception as e:
            log.error(f"Error mapping user webhook data to update DTO: {str(e)}")
            raise
