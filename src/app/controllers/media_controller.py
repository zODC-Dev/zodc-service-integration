import urllib.parse
from uuid import UUID

from fastapi import HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.media import MediaResponse
from src.app.services.media_service import MediaApplicationService
from src.configs.logger import log


class MediaController:
    def __init__(self, media_service: MediaApplicationService):
        self.media_service = media_service

    async def upload_media(self, file: UploadFile, user_id: int) -> StandardResponse[MediaResponse]:
        try:
            media = await self.media_service.upload_media(file, user_id)
            return StandardResponse(
                message="File uploaded successfully",
                data=MediaResponse(
                    media_id=str(media.media_id),
                    filename=media.filename,
                    content_type=media.content_type,
                    size=media.size,
                )
            )
        except Exception as e:
            log.error(f"Failed to upload file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file: {str(e)}"
            ) from e

    async def get_media(self, media_id: UUID) -> StreamingResponse:
        try:
            log.info(f"Media ID: {media_id}")
            media, file_stream, _ = await self.media_service.get_media(media_id)

            log.info(f"Media: {media}")

            # Properly encode the filename for Content-Disposition header
            encoded_filename = urllib.parse.quote(media.filename)

            return StreamingResponse(
                content=file_stream,
                media_type=media.content_type,
                headers={
                    "Access-Control-Expose-Headers": "*",
                    "Content-Disposition": f"attachment; filename={encoded_filename}; filesize={media.size}; filetype={media.content_type}"
                }
            )
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"Failed to get media: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get media: {str(e)}"
            ) from e

    async def remove_media(self, media_id: UUID) -> StandardResponse:
        try:
            success, message = await self.media_service.remove_media(media_id)
            if not success:
                raise HTTPException(status_code=404, detail=message)

            return StandardResponse(
                message=message,
                data=None
            )
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"Failed to remove media: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to remove media: {str(e)}"
            ) from e
