from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from src.domain.models.database.media import MediaDBCreateDTO
from src.domain.models.media import MediaModel


class IMediaRepository(ABC):
    @abstractmethod
    async def create(self, session: AsyncSession, media: MediaDBCreateDTO) -> MediaModel:
        """Create new media record"""
        pass

    @abstractmethod
    async def get_by_id(self, session: AsyncSession, media_id: UUID) -> Optional[MediaModel]:
        """Get media by id"""
        pass

    @abstractmethod
    async def get_by_user(self, session: AsyncSession, user_id: int) -> List[MediaModel]:
        """Get all media uploaded by user"""
        pass

    @abstractmethod
    async def delete(self, session: AsyncSession, media_id: UUID) -> bool:
        """Delete media by id (soft delete)"""
        pass
