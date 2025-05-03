from datetime import datetime, timezone
from typing import Any, Dict

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.configs.logger import log
from src.domain.constants.jira import JiraWebhookEvent
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira.webhooks.jira_webhook import JiraUserWebhookDTO
from src.domain.models.jira.webhooks.mappers.jira_user_webhook_mapper import JiraUserWebhookMapper
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_user_api_service import IJiraUserAPIService
from src.domain.services.jira_user_database_service import IJiraUserDatabaseService


class UserUpdateWebhookHandler(JiraWebhookHandler):
    """Handler for user update webhooks"""

    def __init__(
        self,
        user_database_service: IJiraUserDatabaseService,
        sync_log_repository: ISyncLogRepository,
        jira_user_api_service: IJiraUserAPIService
    ):
        self.sync_log_repository = sync_log_repository
        self.jira_user_api_service = jira_user_api_service
        self.user_database_service = user_database_service

    async def can_handle(self, webhook_event: str) -> bool:
        """Check if this handler can process the given webhook event"""
        return webhook_event in [JiraWebhookEvent.USER_UPDATED, "jira:user_updated"]

    async def handle(self, session: AsyncSession, webhook_data: JiraUserWebhookDTO) -> Dict[str, Any]:
        """Handle the user update webhook"""
        account_id = webhook_data.user.account_id
        log.info(f"Processing user update webhook for user {account_id}")

        # Get latest user data from Jira API
        user_data = await self.get_user_details_from_api(account_id)

        try:
            # Check if user exists
            existing_user = await self.user_database_service.get_user_by_jira_account_id(session=session, jira_account_id=account_id)

            if not existing_user:
                # If we couldn't get data from API, use the webhook data
                if not user_data:
                    log.warning(f"Could not fetch user {account_id} from API, using webhook data")
                    create_dto = JiraUserWebhookMapper.map_to_create_dto(webhook_data)
                else:
                    # Create user create DTO using API data
                    create_dto = JiraUserDBCreateDTO(
                        jira_account_id=user_data.jira_account_id,
                        name=user_data.name,
                        email=user_data.email or "",
                        is_active=user_data.is_active,
                        avatar_url=user_data.avatar_url or "",
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc)
                    )

                # Create new user
                created_user = await self.user_database_service.create_user(session=session, user_data=create_dto)
                operation_type = OperationType.CREATE
                success = created_user is not None

                log.info(f"User {account_id} created in database")
            else:
                # Update existing user
                log.info(f"Updating existing user {account_id}")

                # If we couldn't get data from API, use the webhook data
                if not user_data:
                    log.warning(f"Could not fetch user {account_id} from API, using webhook data")
                    update_dto = JiraUserWebhookMapper.map_to_update_dto(webhook_data)
                else:
                    # Create update DTO using API data
                    update_dto = JiraUserDBUpdateDTO(
                        name=user_data.name,
                        email=user_data.email,
                        is_active=user_data.is_active,
                        avatar_url=user_data.avatar_url,
                        updated_at=datetime.now(timezone.utc)
                    )

                updated_user = await self.user_database_service.update_user_by_jira_account_id(session=session, jira_account_id=account_id, user_data=update_dto)
                operation_type = OperationType.UPDATE
                success = updated_user is not None

                log.info(f"User {account_id} updated in database")

            # Log sync event
            await self.sync_log_repository.create_sync_log(
                session=session,
                sync_log=SyncLogDBCreateDTO(
                    entity_type=EntityType.USER,
                    entity_id=account_id,
                    operation=operation_type,
                    request_payload=webhook_data.model_dump(),
                    response_status=200 if success else 500,
                    response_body={},
                    source=SourceType.WEBHOOK,
                    sender=None
                )
            )

            if not success:
                return {"error": f"Failed to {'update' if existing_user else 'create'} user {account_id}"}

            return {
                "account_id": account_id,
                "created": not existing_user,
                "updated": existing_user is not None
            }

        except Exception as e:
            log.error(f"Error handling user update webhook: {str(e)}")
            return {"error": f"Error processing user {account_id}: {str(e)}"}
