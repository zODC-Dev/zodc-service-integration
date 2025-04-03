from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.models.media import Media


class IMediaRepository(ABC):
    @abstractmethod
    async def create(self, media: Media) -> Media:
        """Create new media record"""
        pass

    @abstractmethod
    async def get_by_id(self, media_id: UUID) -> Optional[Media]:
        """Get media by id"""
        pass

    @abstractmethod
    async def get_by_user(self, user_id: int) -> List[Media]:
        """Get all media uploaded by user"""
        pass
