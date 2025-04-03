from uuid import UUID, uuid4

from src.domain.models.base import BaseModel


class Media(BaseModel):
    media_id: UUID = uuid4()
    filename: str
    blob_url: str
    content_type: str
    size: int
    uploaded_by: int
    container_name: str = "media-files"
