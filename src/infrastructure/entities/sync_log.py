from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, CheckConstraint, Column
from sqlmodel import Field

from src.infrastructure.entities.base import BaseEntityWithTimestamps


class SyncLogEntity(BaseEntityWithTimestamps, table=True):
    __tablename__ = "sync_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    entity_type: str
    entity_id: str
    operation: str
    request_payload: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    response_status: Optional[int] = None
    response_body: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    error_message: Optional[str] = None
    sender: Optional[int] = Field(default=None, foreign_key="jira_users.user_id")
    source: str
    created_at: datetime = Field(default_factory=datetime.now)

    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('ISSUE', 'PROJECT', 'SPRINT', 'USER')",
            name="valid_entity_type"
        ),
        CheckConstraint(
            "operation IN ('CREATE', 'UPDATE', 'DELETE', 'SYNC')",
            name="valid_operation"
        ),
        CheckConstraint(
            "source IN ('NATS', 'WEBHOOK', 'MANUAL')",
            name="valid_source"
        ),
    )
