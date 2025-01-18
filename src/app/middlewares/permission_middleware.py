from functools import wraps
from typing import List

from fastapi import HTTPException, Request
import jwt

from src.configs.auth import JWT_SETTINGS
from src.configs.logger import log
from src.domain.services.permission_service import IPermissionService


def require_permissions(permissions: List[str], scope: str):
    """Require permissions middleware."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, permission_service: IPermissionService, **kwargs):
            # Extract token from request headers
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                raise HTTPException(
                    status_code=401, detail="Missing or invalid token")

            # Verify JWT token
            access_token = auth_header.split(' ')[1]

            try:
                # Decode token to get user_id
                payload = jwt.decode(
                    access_token,
                    JWT_SETTINGS["SECRET_KEY"],
                    algorithms=[JWT_SETTINGS["ALGORITHM"]]
                )
                user_id = int(payload.get("sub"))

                # Get project_id from path parameters if scope is project
                project_id = None
                if scope == "project":
                    project_id = kwargs.get("project_id")
                    if not project_id:
                        raise HTTPException(
                            status_code=400,
                            detail="Project ID is required for project-scoped permissions"
                        )

                # Check cached permissions first
                all_permissions_allowed = True
                missing_permissions = []

                for permission in permissions:
                    cached_permission = await permission_service.get_cached_permission(
                        user_id=user_id,
                        permission=permission,
                        scope=scope,
                        project_id=project_id
                    )
                    log.info(f"Cached permission: {cached_permission}")
                    if not cached_permission or not cached_permission.allowed:
                        missing_permissions.append(permission)
                        all_permissions_allowed = False

                if not all_permissions_allowed:
                    # Verify permissions with auth service
                    verification = await permission_service.verify_permissions(
                        token=access_token,
                        user_id=user_id,
                        permissions=missing_permissions,
                        scope=scope,
                        project_id=project_id
                    )

                    if not verification.allowed:
                        raise HTTPException(
                            status_code=403,
                            detail="Permission denied"
                        )

                    # Cache the result
                    await permission_service.cache_permissions(verification)

                return await func(request, *args, **kwargs)

            except jwt.PyJWTError as e:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid authentication token"
                ) from e

        return wrapper
    return decorator
