from typing import Any, Dict

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_project_service import JiraProjectApplicationService
from src.configs.logger import log
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

    async def handle(self, subject: str, message: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
        # Parse request data
        request = JiraProjectSyncNATSRequestDTO.model_validate(message)

        log.info(f"[NATS] Starting project sync for {request.project_key}")

        try:
            # Call service to handle sync - passing the session parameter
            result = await self.jira_project_service.sync_project(session, request)

            log.info(f"[NATS] Completed project sync for {request.project_key}")

            # Return the result with the synced users
            return result.model_dump()

        except Exception as e:
            log.error(f"[NATS] Error in project sync for {request.project_key}: {str(e)}")
            # Error logs are now handled inside the sync_project method
            raise
