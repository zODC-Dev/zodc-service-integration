from typing import Any, Dict, Mapping

from src.configs.database import AsyncSessionManager
from src.configs.logger import log
from src.domain.services.nats_event_service import INATSEventService
from src.domain.services.nats_message_handler import INATSMessageHandler, INATSRequestHandler
from src.domain.services.nats_service import INATSService


class NATSEventService(INATSEventService):
    def __init__(
        self,
        nats_service: INATSService,
        message_handlers: Mapping[str, INATSMessageHandler],
        request_handlers: Mapping[str, INATSRequestHandler]
    ):
        self.nats_service = nats_service
        self.message_handlers = message_handlers
        self.request_handlers = request_handlers

    async def start(self) -> None:
        """Start all message and request handlers"""
        for message_subject, message_handler in self.message_handlers.items():
            await self.register_message_handler(message_subject, message_handler)

        for request_subject, request_handler in self.request_handlers.items():
            await self.register_request_handler(request_subject, request_handler)

    async def register_message_handler(
        self,
        subject: str,
        handler: INATSMessageHandler
    ) -> None:
        """Register a message handler for a subject"""
        async def message_callback(subject: str, data: Dict[str, Any]) -> None:
            # Use the centralized session manager
            async with AsyncSessionManager.session() as session:
                try:
                    # Process message with handler
                    await handler.handle(subject, data, session)
                except Exception as e:
                    log.error(f"Error handling message for {subject}: {str(e)}")
                    raise

        await self.nats_service.subscribe(subject, message_callback)
        log.info(f"Registered message handler for {subject}")

    async def register_request_handler(
        self,
        subject: str,
        handler: INATSRequestHandler
    ) -> None:
        """Register a request handler for a subject"""
        async def request_callback(subject: str, data: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Use the centralized session manager
                async with AsyncSessionManager.session() as session:
                    # Process request with handler
                    result = await handler.handle(subject, data, session)

                    return {
                        "success": True,
                        "data": result
                    }
            except Exception as e:
                log.error(f"Error handling request for {subject}: {str(e)}")
                return {
                    "success": False,
                    "error": str(e)
                }

        await self.nats_service.subscribe_request(subject, request_callback)
        log.info(f"Registered request handler for {subject}")
