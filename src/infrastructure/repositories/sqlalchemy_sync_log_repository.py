
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.sync_log import SyncLogCreateDTO
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.infrastructure.entities.sync_log import SyncLogEntity


class SQLAlchemySyncLogRepository(ISyncLogRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_sync_log(
        self,
        sync_log: SyncLogCreateDTO
    ) -> SyncLogEntity:
        sync_log = SyncLogEntity(
            entity_type=sync_log.entity_type,
            entity_id=sync_log.entity_id,
            operation=sync_log.operation,
            request_payload=sync_log.request_payload,
            response_status=sync_log.response_status,
            response_body=sync_log.response_body,
            source=sync_log.source,
            sender=sync_log.sender,
            error_message=sync_log.error_message,
        )
        self.session.add(sync_log)
        await self.session.commit()
        return sync_log

    async def update_sync_log(self, sync_log_id: int, **kwargs) -> None:
        pass
