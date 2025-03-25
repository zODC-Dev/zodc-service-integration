from abc import ABC, abstractmethod

from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.sync_log import SyncLogModel


class ISyncLogRepository(ABC):
    @abstractmethod
    async def create_sync_log(self, sync_log: SyncLogDBCreateDTO) -> SyncLogModel:
        pass

    @abstractmethod
    async def update_sync_log(self, sync_log_id: int, **kwargs) -> None:
        pass
