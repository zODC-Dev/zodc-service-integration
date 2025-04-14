from typing import Optional
from uuid import UUID

from src.domain.models.base import BaseModel


class MediaModel(BaseModel):
    media_id: Optional[UUID] = None
    filename: str
    blob_url: str
    content_type: str
    size: int
    uploaded_by: int
    container_name: str = "media-files"
