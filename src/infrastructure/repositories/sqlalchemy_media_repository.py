from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.database.media import MediaDBCreateDTO
from src.domain.models.media import MediaModel
from src.domain.repositories.media_repository import IMediaRepository
from src.infrastructure.entities.media import MediaEntity


class SQLAlchemyMediaRepository(IMediaRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, media: MediaDBCreateDTO) -> MediaModel:
        db_media = MediaEntity(
            media_id=media.media_id,
            filename=media.filename,
            blob_url=media.blob_url,
            content_type=media.content_type,
            size=media.size,
            uploaded_by=media.uploaded_by,
            container_name=media.container_name
        )
        self.session.add(db_media)
        await self.session.commit()
        await self.session.refresh(db_media)
        return MediaModel.model_validate(db_media.model_dump())

    async def get_by_id(self, media_id: UUID) -> Optional[MediaModel]:
        result = await self.session.exec(
            select(MediaEntity).where(col(MediaEntity.media_id) == media_id, col(MediaEntity.deleted_at).is_(None))
        )
        media = result.first()
        return MediaModel.model_validate(media.model_dump()) if media else None

    async def get_by_user(self, user_id: int) -> List[MediaModel]:
        result = await self.session.exec(
            select(MediaEntity).where(col(MediaEntity.uploaded_by) == user_id, col(MediaEntity.deleted_at).is_(None))
        )
        media_list = result.all()
        return [MediaModel.model_validate(media.model_dump()) for media in media_list]

    async def delete(self, media_id: UUID) -> bool:
        """Soft delete media by setting deleted_at timestamp"""
        result = await self.session.exec(
            select(MediaEntity).where(col(MediaEntity.media_id) == media_id, col(MediaEntity.deleted_at).is_(None))
        )
        media = result.first()

        if not media:
            return False

        media.deleted_at = datetime.now()
        self.session.add(media)
        await self.session.commit()
        return True
