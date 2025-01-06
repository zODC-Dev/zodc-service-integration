from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Dict

MessageCallback = Callable[[str, Dict[str, Any]], Awaitable[None]]


class INATSService(ABC):
    """Interface for NATS messaging service"""

    @abstractmethod
    async def connect(self) -> None:
        """Connect to NATS server"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from NATS server"""
        pass

    @abstractmethod
    async def publish(self, subject: str, message: Dict[str, Any]) -> None:
        """Publish message to a subject"""
        pass

    @abstractmethod
    async def subscribe(self, subject: str, callback: MessageCallback) -> None:
        """Subscribe to a subject"""
        pass

    @abstractmethod
    async def request(self, subject: str, message: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        """Send request and wait for response"""
        pass
