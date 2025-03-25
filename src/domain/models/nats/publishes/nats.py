from typing import Any, Dict

from src.domain.models.nats.nats_message import NATSMessageBaseDTO


class NATSPublishDTO(NATSMessageBaseDTO):
    event_type: str
    data: Dict[str, Any]
