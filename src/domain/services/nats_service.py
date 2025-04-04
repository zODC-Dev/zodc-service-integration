from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine, Dict, List, Optional, Protocol, TypeVar

T = TypeVar('T')
R = TypeVar('R')

# MessageCallback = Callable[[str, Dict[str, Any] | List[Dict[str, Any]]], Awaitable[None]]
MessageCallback = Callable[[str, Dict[str, Any]], Coroutine[Any, Any, None]
                           ] | Callable[[str, List[Dict[str, Any]]], Coroutine[Any, Any, None]]


class MessageHandler(Protocol):
    async def __call__(self, subject: str, data: Dict[str, Any]) -> None: ...


class RequestHandler(Protocol):
    async def __call__(self, subject: str, data: Dict[str, Any]) -> Dict[str, Any]: ...


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
        """Publish a message to a topic"""
        pass

    @abstractmethod
    async def subscribe(self, subject: str, callback: MessageHandler) -> None:
        """Subscribe to a topic for pub/sub pattern"""
        pass

    @abstractmethod
    async def subscribe_request(self, subject: str, callback: RequestHandler) -> None:
        """Subscribe to a topic for request-reply pattern"""
        pass

    @abstractmethod
    async def request(self, subject: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request and wait for reply"""
        pass
