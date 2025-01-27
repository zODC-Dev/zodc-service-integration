from fastapi import Depends

from src.app.controllers.microsoft_calendar_controller import MicrosoftCalendarController
from src.app.dependencies.common import get_redis_service
from src.app.services.microsoft_calendar_service import MicrosoftCalendarApplicationService
from src.infrastructure.services.microsoft_calendar_service import MicrosoftCalendarService
from src.infrastructure.services.redis_service import RedisService


def get_microsoft_calendar_service(
    redis_service: RedisService = Depends(get_redis_service)
) -> MicrosoftCalendarService:
    """Get Microsoft Calendar service."""
    return MicrosoftCalendarService(redis_service=redis_service)


def get_microsoft_calendar_application_service(
    calendar_service: MicrosoftCalendarService = Depends(get_microsoft_calendar_service)
) -> MicrosoftCalendarApplicationService:
    """Get Microsoft Calendar application service."""
    return MicrosoftCalendarApplicationService(calendar_service=calendar_service)


def get_microsoft_calendar_controller(
    calendar_service: MicrosoftCalendarApplicationService = Depends(get_microsoft_calendar_application_service)
) -> MicrosoftCalendarController:
    """Get Microsoft Calendar controller."""
    return MicrosoftCalendarController(calendar_service=calendar_service)
