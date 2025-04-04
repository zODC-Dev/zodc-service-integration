from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel


class NATSMessage:
    def __init__(
        self,
        subject: str,
        data: Dict[str, Any],
        timestamp: datetime = datetime.utcnow()
    ):
        self.subject = subject
        self.data = data
        self.timestamp = timestamp


class NATSRequest(NATSMessage):
    def __init__(
        self,
        subject: str,
        data: Dict[str, Any],
        user_id: Optional[int] = None,
        timestamp: datetime = datetime.utcnow()
    ):
        super().__init__(subject, data, timestamp)
        self.user_id = user_id


class NATSResponse(NATSMessage):
    def __init__(
        self,
        subject: str,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        timestamp: datetime = datetime.utcnow()
    ):
        super().__init__(subject, data or {}, timestamp)
        self.success = success
        self.error = error


class NATSEvent(NATSMessage):
    def __init__(
        self,
        subject: str,
        event_type: str,
        data: Dict[str, Any],
        timestamp: datetime = datetime.now(timezone.utc)
    ):
        super().__init__(subject, data, timestamp)
        self.event_type = event_type


class NATSMessageBaseDTO(BaseModel):
    subject: str
    timestamp: datetime = datetime.now(timezone.utc)
