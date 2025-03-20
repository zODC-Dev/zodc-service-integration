from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class NATSMessageBaseDTO(BaseModel):
    subject: str
    timestamp: datetime = datetime.utcnow()


class NATSRequestDTO(NATSMessageBaseDTO):
    data: Dict[str, Any]
    user_id: Optional[int] = None


class NATSResponseDTO(NATSMessageBaseDTO):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class NATSEventDTO(NATSMessageBaseDTO):
    event_type: str
    data: Dict[str, Any]
