from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlmodel import JSON, CheckConstraint, Column, DateTime, Field, SQLModel


class SyncLogEntity(SQLModel, table=True):
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
    status: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

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
