from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.permission import PermissionVerificationResponse


class IPermissionService(ABC):
    @abstractmethod
    async def verify_permissions(
        self,
        token: str,
        user_id: int,
        permissions: List[str],
        scope: str,
        project_id: Optional[int] = None
    ) -> PermissionVerificationResponse:
        """Verify multiple permissions at once"""
        pass

    @abstractmethod
    async def cache_permissions(
        self,
        response: PermissionVerificationResponse,
        expiry: int = 300
    ) -> None:
        """Cache multiple permissions verification result"""
        pass

    @abstractmethod
    async def get_cached_permission(
        self,
        user_id: int,
        permission: str,
        scope: str,
        project_id: Optional[int] = None
    ) -> Optional[PermissionVerificationResponse]:
        """Get cached permission verification result"""
        pass
