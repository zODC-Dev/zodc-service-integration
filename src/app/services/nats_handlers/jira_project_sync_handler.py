from datetime import datetime, timezone
from typing import Any, Dict

from src.app.services.jira_project_service import JiraProjectApplicationService
from src.configs.logger import log
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.nats.requests.jira_project import JiraProjectSyncNATSRequestDTO
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.nats_message_handler import INATSRequestHandler


class JiraProjectSyncRequestHandler(INATSRequestHandler):
    def __init__(
        self,
        jira_project_service: JiraProjectApplicationService,
        sync_log_repository: ISyncLogRepository
    ):
        self.jira_project_service = jira_project_service
        self.sync_log_repository = sync_log_repository

    async def handle(self, subject: str, data: Dict[str, Any]) -> Dict[str, Any]:
        # Parse request data
        request = JiraProjectSyncNATSRequestDTO.model_validate(data)

        # Create sync log entry
        sync_log = await self._create_sync_log(request)

        try:
            # Call service to handle sync
            result = await self.jira_project_service.sync_project(request)

            # Update sync log with success
            await self._update_sync_log(sync_log.id, True)

            # The result now includes synced_users
            return result.model_dump()

        except Exception as e:
            # Update sync log with error
            await self._update_sync_log(sync_log.id, False, str(e))
            raise

    async def _create_sync_log(self, request: JiraProjectSyncNATSRequestDTO):
        """Create initial sync log entry for project sync request"""
        sync_log_data = SyncLogDBCreateDTO(
            entity_type=EntityType.PROJECT,
            entity_id=request.project_key,
            operation=OperationType.SYNC,
            source=SourceType.NATS,
            sender=request.user_id,
            request_payload=request.model_dump(),
            created_at=datetime.now(timezone.utc),
            status="PROCESSING"
        )

        return await self.sync_log_repository.create_sync_log(sync_log_data)

    async def _update_sync_log(
        self,
        sync_log_id: int,
        success: bool,
        error_message: str = None
    ) -> None:
        """Update sync log status after processing"""
        try:
            update_data = {
                "status": "SUCCESS" if success else "ERROR",
                "completed_at": datetime.now(timezone.utc),
            }

            if error_message:
                update_data["error_message"] = error_message

            await self.sync_log_repository.update_sync_log(
                sync_log_id=sync_log_id,
                **update_data
            )
        except Exception as e:
            # Log error but don't raise since this is cleanup code
            log.error(f"Failed to update sync log {sync_log_id}: {str(e)}")
