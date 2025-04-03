from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field

from src.infrastructure.entities.base import BaseEntityWithTimestamps


class MediaEntity(BaseEntityWithTimestamps, table=True):
    __tablename__ = "media"

    id: Optional[int] = Field(default=None, primary_key=True)
    media_id: UUID = Field(default_factory=uuid4, index=True)
    filename: str
    blob_url: str
    content_type: str
    size: int
    uploaded_by: int = Field(foreign_key="jira_users.user_id")
    container_name: str = "media-files"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
