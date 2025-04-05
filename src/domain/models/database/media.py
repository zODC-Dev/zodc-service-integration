from uuid import UUID

from pydantic import BaseModel


class MediaDBCreateDTO(BaseModel):
    media_id: UUID = None
    filename: str
    blob_url: str
    content_type: str
    size: int
    uploaded_by: int
    container_name: str = "media-files"
