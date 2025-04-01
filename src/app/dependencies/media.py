from fastapi import Depends

from src.app.controllers.media_controller import MediaController
from src.app.services.media_service import MediaService
from src.configs.database import get_db
from src.domain.repositories.media_repository import IMediaRepository
from src.infrastructure.repositories.sqlalchemy_media_repository import SQLAlchemyMediaRepository
from src.infrastructure.services.azure_blob_storage_service import AzureBlobStorageService


async def get_media_repository(session=Depends(get_db)) -> IMediaRepository:
    """Get the media repository"""
    return SQLAlchemyMediaRepository(session)


async def get_media_service(
    media_repository: IMediaRepository = Depends(get_media_repository),
    blob_storage_service: AzureBlobStorageService = Depends(AzureBlobStorageService)
) -> MediaService:
    """Get the media service"""
    return MediaService(
        media_repository=media_repository,
        blob_storage_service=blob_storage_service
    )


async def get_media_controller(
    media_service: MediaService = Depends(get_media_service)
) -> MediaController:
    """Get the media controller"""
    return MediaController(media_service=media_service)
