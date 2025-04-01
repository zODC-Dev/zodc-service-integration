from typing import Optional
from uuid import UUID

from fastapi import UploadFile

from src.domain.entities.media import Media
from src.domain.repositories.media_repository import IMediaRepository
from src.domain.services.blob_storage_service import IBlobStorageService


class MediaService:
    def __init__(
        self,
        media_repository: IMediaRepository,
        blob_storage_service: IBlobStorageService
    ):
        self.media_repository = media_repository
        self.blob_storage_service = blob_storage_service

    async def upload_media(self, file: UploadFile, user_id: int) -> Media:
        # Upload to blob storage
        blob_url = await self.blob_storage_service.upload_file(
            file=file,
            container_name="media-files"
        )

        # Create media record
        media = Media(
            filename=file.filename,
            blob_url=blob_url,
            content_type=file.content_type,
            size=file.size,
            uploaded_by=user_id
        )

        return await self.media_repository.create(media)

    async def get_media(self, media_id: UUID) -> Optional[Media]:
        return await self.media_repository.get_by_id(media_id)
