from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.database.media import MediaDBCreateDTO
from src.domain.models.media import MediaModel
from src.domain.repositories.media_repository import IMediaRepository
from src.infrastructure.entities.media import MediaEntity


class SQLAlchemyMediaRepository(IMediaRepository):
    def __init__(self):
        pass

    async def create(self, session: AsyncSession, media: MediaDBCreateDTO) -> MediaModel:
        """Create a new media entry"""
        try:
            db_media = MediaEntity(
                media_id=media.media_id,
                filename=media.filename,
                blob_url=media.blob_url,
                content_type=media.content_type,
                size=media.size,
                uploaded_by=media.uploaded_by,
                container_name=media.container_name
            )

            session.add(db_media)
            # Let the session manager handle the transaction
            await session.flush()
            await session.refresh(db_media)

            return MediaModel.model_validate(db_media.model_dump())
        except Exception as e:
            log.error(f"Error creating media: {str(e)}")
            raise

    async def get_by_id(self, session: AsyncSession, media_id: UUID) -> Optional[MediaModel]:
        """Get media by ID"""
        try:
            result = await session.exec(
                select(MediaEntity).where(col(MediaEntity.media_id) == media_id, col(MediaEntity.deleted_at).is_(None))
            )
            media = result.first()
            if not media:
                return None

            return MediaModel.model_validate(media.model_dump())
        except Exception as e:
            log.error(f"Error getting media by ID: {str(e)}")
            raise

    async def get_by_user(self, session: AsyncSession, user_id: int) -> List[MediaModel]:
        result = await session.exec(
            select(MediaEntity).where(col(MediaEntity.uploaded_by) == user_id, col(MediaEntity.deleted_at).is_(None))
        )
        medias = result.all()
        return [MediaModel.model_validate(media.model_dump()) for media in medias]

    async def delete(self, session: AsyncSession, media_id: UUID) -> bool:
        """Soft delete media by setting deleted_at timestamp"""
        result = await session.exec(
            select(MediaEntity).where(col(MediaEntity.media_id) == media_id, col(MediaEntity.deleted_at).is_(None))
        )
        media = result.first()

        if not media:
            return False

        media.deleted_at = datetime.now()
        session.add(media)
        # Let the session manager handle the transaction
        await session.flush()
        return True
