from abc import ABC, abstractmethod

from src.domain.services.nats_message_handler import INATSMessageHandler, INATSRequestHandler


class INATSEventService(ABC):
    """Interface for NATS event orchestration"""

    @abstractmethod
    async def start(self) -> None:
        """Start all NATS subscribers and request handlers"""
        pass

    @abstractmethod
    async def register_message_handler(
        self,
        subject: str,
        handler: INATSMessageHandler
    ) -> None:
        """Register a message handler for a subject"""
        pass

    @abstractmethod
    async def register_request_handler(
        self,
        subject: str,
        handler: INATSRequestHandler
    ) -> None:
        """Register a request handler for a subject"""
        pass
