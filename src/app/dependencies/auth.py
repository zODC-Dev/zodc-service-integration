from functools import partial
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends

from src.app.middlewares.auth_middleware import JWTAuth


def require_auth(
    *,
    system_roles: Optional[List[str]] = None,
    project_roles: Optional[List[str]] = None,
    permissions: Optional[List[str]] = None,
    require_all: bool = False
) -> Callable[[Any], Dict[str, Any]]:
    """Factory function for creating auth dependencies"""
    auth_dependency = JWTAuth(
        required_system_roles=system_roles,
        required_project_roles=project_roles,
        required_permissions=permissions,
        require_all_roles=require_all
    )
    return Depends(auth_dependency)  # type: ignore


# Common auth patterns as class attributes
require_admin = staticmethod(partial(require_auth, system_roles=["admin"]))
require_user = staticmethod(partial(require_auth, system_roles=["user"]))
require_project_admin = staticmethod(partial(require_auth, project_roles=["project_admin"]))
require_project_management = staticmethod(
    partial(
        require_auth,
        project_roles=["project_admin"],
        require_all=True
    )
)
