from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.infrastructure.entities.sync_log import SyncLogEntity


class SyncLogModel(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    operation: str
    status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @classmethod
    def from_entity(cls, entity: SyncLogEntity) -> "SyncLogModel":
        return cls(
            id=entity.id,
            entity_type=entity.entity_type,
            entity_id=entity.entity_id,
            operation=entity.operation,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
