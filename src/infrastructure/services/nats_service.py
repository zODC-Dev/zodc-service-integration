import json
from typing import Any, Callable, Coroutine, Dict, List

from nats.aio.client import Client
from nats.aio.msg import Msg

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.services.nats_service import INATSService, MessageCallback


class NATSService(INATSService):
    def __init__(self) -> None:
        self._client: Client = Client()
        self._is_connected: bool = False

    async def connect(self) -> None:
        """Connect to NATS server"""
        try:
            if not self._is_connected:
                await self._client.connect(
                    servers=[settings.NATS_URL],
                    name=settings.NATS_CLIENT_NAME,
                    reconnect_time_wait=3,
                    max_reconnect_attempts=5,
                    connect_timeout=5,
                    user=settings.NATS_USERNAME,
                    password=settings.NATS_PASSWORD
                )
                self._is_connected = True
                log.info(f"Connected to NATS server at {settings.NATS_URL}")
        except Exception as e:
            log.error(f"Failed to connect to NATS: {str(e)}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from NATS server"""
        if self._is_connected:
            await self._client.drain()
            self._is_connected = False
            log.info("Disconnected from NATS server")

    async def publish(self, subject: str, message: Dict[str, Any] | List[Dict[str, Any]]) -> None:
        """Publish message to a subject"""
        try:
            if not self._is_connected:
                await self.connect()

            payload = json.dumps(message).encode()
            await self._client.publish(subject, payload)
            log.info(f"Published message to {subject}: {message}")
        except Exception as e:
            log.error(f"Failed to publish message: {str(e)}")
            raise

    async def subscribe(self, subject: str, callback: MessageCallback) -> None:
        """Subscribe to a subject for pub/sub pattern"""
        try:
            if not self._is_connected:
                await self.connect()

            async def message_handler(msg: Msg) -> None:
                try:
                    data = json.loads(msg.data.decode())
                    await callback(msg.subject, data)
                except Exception as e:
                    log.error(f"Error processing message: {str(e)}")

            await self._client.subscribe(subject, cb=message_handler)
            log.info(f"Subscribed to {subject}")
        except Exception as e:
            log.error(f"Failed to subscribe: {str(e)}")
            raise

    async def subscribe_request(self, subject: str, callback: Callable[[str, Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]) -> None:
        """Subscribe to a subject for request-reply pattern"""
        try:
            if not self._is_connected:
                await self.connect()

            async def request_handler(msg: Msg) -> None:
                try:
                    # Parse request data
                    data = json.loads(msg.data.decode())

                    # Process request and get response
                    response = await callback(msg.subject, data)

                    # Send response back
                    response_data = json.dumps(response).encode()
                    await msg.respond(response_data)

                    log.info(f"Handled request for {msg.subject} with response: {response}")
                except Exception as e:
                    # Send error response
                    error_response = json.dumps({"error": str(e)}).encode()
                    await msg.respond(error_response)
                    log.error(f"Error handling request: {str(e)}")

            # Subscribe with queue group for load balancing if needed
            await self._client.subscribe(
                subject,
                cb=request_handler,
                queue=f"{subject}_queue"  # Optional: Enable queue group for load balancing
            )
            log.info(f"Subscribed to requests on {subject}")
        except Exception as e:
            log.error(f"Failed to subscribe to requests: {str(e)}")
            raise

    async def request(self, subject: str, message: Dict[str, Any], timeout: int = 10) -> Dict[str, Any]:
        """Send request and wait for response"""
        try:
            if not self._is_connected:
                await self.connect()

            payload = json.dumps(message).encode()
            response = await self._client.request(subject, payload, timeout=timeout)

            if not response.data:
                return {}

            response_data: Dict[str, Any] = json.loads(response.data.decode())

            # Check for error in response
            if isinstance(response_data, dict) and "error" in response_data:
                raise Exception(response_data["error"])

            return response_data

        except Exception as e:
            log.error(f"Failed to send request: {str(e)}")
            raise
