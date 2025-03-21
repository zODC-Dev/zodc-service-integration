from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SyncLogModel(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    operation: str
    status: str
    created_at: datetime
    updated_at: datetime


class SyncLogCreateDTO(BaseModel):
    entity_type: str
    entity_id: str
    operation: str
    source: str
    sender: Optional[int] = None
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    response_status: Optional[int] = None
    response_body: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
