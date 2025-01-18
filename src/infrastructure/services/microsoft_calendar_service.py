from datetime import datetime
from typing import Any, Dict, Optional

from httpx import AsyncClient
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.entities.microsoft_calendar_event import MicrosoftCalendarEvent, MicrosoftCalendarEventsList
from src.domain.exceptions.microsoft_calendar_exceptions import CalendarError, CalendarTokenError
from src.domain.services.microsoft_calendar_service import IMicrosoftCalendarService
from src.infrastructure.services.redis_service import RedisService


class MicrosoftCalendarService(IMicrosoftCalendarService):
    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.timeout = 30

    async def _get_token(self, user_id: int) -> str:
        """Get Microsoft token from cache or auth service."""
        # Try to get token from cache first
        token = await self.redis_service.get_cached_microsoft_token(user_id)
        if token:
            log.info("Using Microsoft token from cache")
            return token

        # If not in cache, request new token from auth service
        async with AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{settings.AUTH_SERVICE_URL}/api/v1/internal/microsoft/token/{user_id}",
            )

            if response.status_code != 200:
                log.error(f"Failed to obtain Microsoft token: {response.text}")
                raise CalendarTokenError("Failed to obtain Microsoft token")

            data = response.json()
            token = data.get("access_token")
            if not token:
                raise CalendarTokenError("Invalid token response from auth service")

            # Cache the token
            await self.redis_service.cache_microsoft_token(user_id, token)
            return token

    async def get_user_events(
        self,
        user_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page_size: int = 50,
        next_link: Optional[str] = None
    ) -> MicrosoftCalendarEventsList:
        try:
            # Get Microsoft token
            token = await self._get_token(user_id)

            # Build URL and params
            url = next_link or f"{self.BASE_URL}/me/calendar/events"
            params = self._build_query_params(
                start_time,
                end_time,
                page_size
            )

            # Call Microsoft Graph API
            async with AsyncClient() as client:
                response = await client.get(
                    url,
                    params=params,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json"
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data)
                else:
                    log.error(
                        f"Microsoft Graph API error: {
                            response.status_code} - {response.text}"
                    )
                    raise CalendarError("Failed to fetch calendar events")

        except Exception as e:
            log.error(f"Calendar repository error: {str(e)}")
            raise CalendarError("Failed to fetch calendar events") from e

    def _build_query_params(
        self,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        page_size: int
    ) -> Dict[str, Any]:
        """Build query parameters for Microsoft Graph API"""
        params = {
            "$top": page_size,
            "$orderby": "start/dateTime",
            "$select": "id,subject,organizer,attendees,start,end,isOnlineMeeting,onlineMeeting"
        }

        if start_time and end_time:
            params["$filter"] = (
                f"start/dateTime ge '{start_time.isoformat()}Z' and "
                f"end/dateTime le '{end_time.isoformat()}Z'"
            )

        return params

    def _parse_event(self, event: Dict[str, Any]) -> MicrosoftCalendarEvent:
        online_meeting = event.get("onlineMeeting")
        online_meeting_url = online_meeting.get(
            "joinUrl") if online_meeting else None
        return MicrosoftCalendarEvent(
            id=event["id"],
            subject=event["subject"],
            start_time=datetime.fromisoformat(
                event["start"]["dateTime"].replace('Z', '')),
            end_time=datetime.fromisoformat(
                event["end"]["dateTime"].replace('Z', '')),
            organizer_email=event["organizer"]["emailAddress"]["address"],
            is_online_meeting=event.get("isOnlineMeeting", False),
            online_meeting_url=online_meeting_url,
            attendees=[
                attendee["emailAddress"]["address"]
                for attendee in event.get("attendees", [])
            ]
        )

    def _parse_response(self, data: Dict[str, Any]) -> MicrosoftCalendarEventsList:
        """Parse Microsoft Graph API response to domain entity"""
        events = [self._parse_event(event) for event in data.get("value", [])]

        return MicrosoftCalendarEventsList(
            events=events,
            next_link=data.get("@odata.nextLink")
        )
