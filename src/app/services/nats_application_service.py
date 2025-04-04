from src.configs.logger import log
from src.domain.models.nats.nats_message import NATSEvent, NATSRequest
from src.domain.models.nats.publishes.nats import NATSPublishDTO
from src.domain.models.nats.replies.nats import NATSReplyDTO
from src.domain.models.nats.requests.nats import NATSRequestDTO
from src.domain.services.nats_service import INATSService


class NATSApplicationService:
    def __init__(self, nats_service: INATSService):
        self.nats_service = nats_service

    async def publish_event(self, event_dto: NATSPublishDTO) -> None:
        """Publish an event to NATS"""
        try:
            event = NATSEvent(
                subject=event_dto.subject,
                event_type=event_dto.event_type,
                data=event_dto.data,
                timestamp=event_dto.timestamp
            )
            await self.nats_service.publish(event.subject, event.data)
        except Exception as e:
            log.error(f"Failed to publish event: {str(e)}")
            raise

    async def send_request(self, request_dto: NATSRequestDTO) -> NATSReplyDTO:
        """Send a request and wait for response"""
        try:
            request = NATSRequest(
                subject=request_dto.subject,
                data=request_dto.data,
                user_id=request_dto.user_id,
                timestamp=request_dto.timestamp
            )
            response_data = await self.nats_service.request(request.subject, request.data)

            return NATSReplyDTO(
                subject=request_dto.subject,
                success=True,
                data=response_data
            )
        except Exception as e:
            log.error(f"Failed to send request: {str(e)}")
            return NATSReplyDTO(
                subject=request_dto.subject,
                success=False,
                error=str(e)
            )
