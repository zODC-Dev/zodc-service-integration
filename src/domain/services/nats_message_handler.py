from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class INATSMessageHandler(ABC):
    """Base interface for NATS message handlers"""
    @abstractmethod
    async def handle(self, subject: str, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a NATS message"""
        pass


class INATSRequestHandler(ABC):
    """Base interface for NATS request-reply handlers"""
    @abstractmethod
    async def handle(self, subject: str, message: Dict[str, Any]) -> Dict[str, Any]:
        pass
