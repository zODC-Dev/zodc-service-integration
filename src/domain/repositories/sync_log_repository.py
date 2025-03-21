from abc import ABC, abstractmethod

from src.domain.models.sync_log import SyncLogCreateDTO, SyncLogModel


class ISyncLogRepository(ABC):
    @abstractmethod
    async def create_sync_log(self, sync_log: SyncLogCreateDTO) -> SyncLogModel:
        pass

    @abstractmethod
    async def update_sync_log(self, sync_log_id: int, **kwargs) -> None:
        pass
