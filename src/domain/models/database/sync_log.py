from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SyncLogDBCreateDTO(BaseModel):
    entity_type: str
    entity_id: str
    operation: str
    source: str
    sender: Optional[int] = None
    request_payload: Dict[str, Any] = Field(default_factory=dict)
    response_status: Optional[int] = None
    response_body: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
