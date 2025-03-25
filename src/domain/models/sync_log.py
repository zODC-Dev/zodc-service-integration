from datetime import datetime

from pydantic import BaseModel


class SyncLogModel(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    operation: str
    status: str
    created_at: datetime
    updated_at: datetime
