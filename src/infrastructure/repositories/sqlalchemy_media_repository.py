from typing import List, Optional
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.entities.media import Media as MediaEntity
from src.domain.repositories.media_repository import IMediaRepository
from src.infrastructure.models.media import Media


class SQLAlchemyMediaRepository(IMediaRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, media: MediaEntity) -> MediaEntity:
        db_media = Media(
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
        return MediaEntity.model_validate(db_media)

    async def get_by_id(self, media_id: UUID) -> Optional[MediaEntity]:
        result = await self.session.exec(
            select(Media).where(Media.media_id == media_id)
        )
        media = result.first()
        return MediaEntity.model_validate(media) if media else None

    async def get_by_user(self, user_id: int) -> List[MediaEntity]:
        result = await self.session.exec(
            select(Media).where(Media.uploaded_by == user_id)
        )
        media_list = result.all()
        return [MediaEntity.model_validate(media) for media in media_list]
