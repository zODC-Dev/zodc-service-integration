from typing import Any, Dict, Optional

from src.domain.models.nats.nats_message import NATSMessageBaseDTO


class NATSRequestDTO(NATSMessageBaseDTO):
    data: Dict[str, Any]
    user_id: Optional[int] = None
