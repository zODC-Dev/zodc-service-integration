from contextlib import asynccontextmanager
from typing import Any, Dict, Mapping

from src.configs.database import AsyncSessionLocal
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
            # Create a session for each message handling
            session = AsyncSessionLocal()
            try:
                # Begin transaction explicitly
                await session.begin()

                # Process message with handler
                await handler.handle(subject, data)

                # Commit if all went well
                await session.commit()
            except Exception as e:
                log.error(f"Error handling message for {subject}: {str(e)}")
                # Rollback on error
                if session.is_active:
                    await session.rollback()
            finally:
                # Always close the session
                if not session.is_active:
                    await session.close()

        await self.nats_service.subscribe(subject, message_callback)
        log.info(f"Registered message handler for {subject}")

    @asynccontextmanager
    async def _get_request_session(self):
        """Context manager to safely handle database session for request handlers"""
        session = AsyncSessionLocal()
        try:
            # Begin transaction explicitly
            await session.begin()
            yield session
            # Commit if no exception occurred
            if session.is_active:
                await session.commit()
        except Exception:
            # Rollback on error
            if session.is_active:
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    log.error(f"Error during session rollback: {str(rollback_error)}")
            raise
        finally:
            # Always close the session when done, but only if not in an active transaction
            try:
                if not session.is_active:
                    await session.close()
            except Exception as close_error:
                log.warning(f"Error closing session: {str(close_error)}")

    async def register_request_handler(
        self,
        subject: str,
        handler: INATSRequestHandler
    ) -> None:
        """Register a request handler for a subject"""
        async def request_callback(subject: str, data: Dict[str, Any]) -> Dict[str, Any]:
            try:
                # Process the request in a dedicated database session
                async with self._get_request_session():
                    # Process request with handler inside transaction
                    result = await handler.handle(subject, data)

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
