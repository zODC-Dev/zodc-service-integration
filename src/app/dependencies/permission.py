from fastapi import Depends

from src.app.dependencies.common import get_redis_service
from src.app.services.permission_service import PermissionService

async def get_permission_service(
    redis_service=Depends(get_redis_service)
) -> PermissionService:
    return PermissionService(redis_service=redis_service) 