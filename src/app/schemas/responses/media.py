from src.app.schemas.responses.base import BaseResponse


class MediaResponse(BaseResponse):
    media_id: str
    filename: str
    content_type: str
    size: int
    download_url: str
