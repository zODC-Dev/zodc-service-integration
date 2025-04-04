from typing import Any, Dict, Optional

from src.domain.models.nats.nats_message import NATSMessageBaseDTO


class NATSReplyDTO(NATSMessageBaseDTO):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
