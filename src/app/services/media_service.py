from typing import AsyncIterator, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile

from src.configs.logger import log
from src.configs.settings import settings
from src.domain.models.database.media import MediaDBCreateDTO
from src.domain.models.media import MediaModel
from src.domain.repositories.media_repository import IMediaRepository
from src.domain.services.blob_storage_service import IBlobStorageService


class MediaApplicationService:
    def __init__(
        self,
        media_repository: IMediaRepository,
        blob_storage_service: IBlobStorageService
    ):
        self.media_repository = media_repository
        self.blob_storage_service = blob_storage_service
        self.container_name = settings.AZURE_STORAGE_ACCOUNT_CONTAINER_NAME

    async def upload_media(self, file: UploadFile, user_id: int) -> MediaModel:
        # Upload to blob storage
        blob_url = await self.blob_storage_service.upload_file(
            file=file,
            container_name=self.container_name
        )

        media_id = uuid4()

        log.info(f"Media ID in create: {media_id}")

        # Create media record
        media = MediaDBCreateDTO(
            media_id=media_id,
            filename=file.filename,
            blob_url=blob_url,
            content_type=file.content_type,
            size=file.size,
            uploaded_by=user_id
        )

        return await self.media_repository.create(media)

    async def get_media(self, media_id: UUID) -> Tuple[MediaModel, AsyncIterator[bytes], int]:
        """Get media file by id

        Returns:
            Tuple[MediaModel, AsyncIterator[bytes], int]: Media info, file content stream and file size
        """
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")

        # Download file from blob storage
        file_stream, file_size = await self.blob_storage_service.download_file(
            filename=media.filename,
            container_name=self.container_name
        )

        return media, file_stream, file_size

    async def remove_media(self, media_id: UUID) -> Tuple[bool, str]:
        """Remove media file from storage and database (soft delete)

        Returns:
            Tuple[bool, str]: Success status and message
        """
        # Get media info first
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            return False, "Media not found"

        # Delete from blob storage
        filename = media.filename
        deleted_from_storage = await self.blob_storage_service.delete_file(
            filename=filename,
            container_name=self.container_name
        )

        # Soft delete from database regardless of storage deletion success
        deleted_from_db = await self.media_repository.delete(media_id)

        if deleted_from_storage and deleted_from_db:
            return True, "Media deleted successfully"
        elif deleted_from_db:
            return True, "Media record deleted but file removal from storage failed"
        else:
            return False, "Failed to delete media"
