import json
from typing import Optional, List

import aiohttp
from fastapi import HTTPException

from src.configs.logger import log
from src.configs.settings import settings

from src.domain.entities.permission import PermissionVerificationResponse
from src.domain.services.permission_service import IPermissionService
from src.infrastructure.services.redis_service import RedisService


class PermissionService(IPermissionService):
    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.auth_service_url = "http://localhost:8000/api/v1/permissions/verify"

    async def verify_permissions(
        self,
        token: str,
        user_id: int,
        permissions: List[str],
        scope: str,
        project_id: Optional[int] = None
    ) -> PermissionVerificationResponse:
        log.info(f"Verifying permissions for user {user_id} with scope {
                 scope} and project {project_id} with permissions {permissions}")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.auth_service_url,
                json={
                    "token": token,
                    "user_id": user_id,
                    "permissions": permissions,
                    "scope": scope,
                    "project_id": project_id
                }
            ) as response:
                if response.status != 200:
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to verify permissions"
                    )
                data = await response.json()
                return PermissionVerificationResponse(**data)

    async def cache_permissions(
        self,
        response: PermissionVerificationResponse,
        expiry: int = 300
    ) -> None:
        """Cache each permission separately for granular access control"""
        for permission in response.permissions:
            key = self._generate_cache_key(
                response.user_id,
                permission,
                response.scope,
                response.project_id
            )
            # Cache individual permission response
            permission_response = PermissionVerificationResponse(
                allowed=response.allowed,
                user_id=response.user_id,
                permissions=[permission],
                scope=response.scope,
                project_id=response.project_id,
                error=response.error
            )
            await self.redis_service.set(key, permission_response.dict(), expiry)

    async def get_cached_permission(
        self,
        user_id: int,
        permission: str,
        scope: str,
        project_id: Optional[int] = None
    ) -> Optional[PermissionVerificationResponse]:
        key = self._generate_cache_key(user_id, permission, scope, project_id)
        cached_data = await self.redis_service.get(key)
        if cached_data:
            return PermissionVerificationResponse(**cached_data)
        return None

    def _generate_cache_key(
        self,
        user_id: int,
        permission: str,
        scope: str,
        project_id: Optional[int] = None
    ) -> str:
        """Generate Redis cache key for permissions"""
        if scope == "system":
            return f"perm:sys:{user_id}:{permission}"
        return f"perm:proj:{user_id}:{permission}:{project_id}"
