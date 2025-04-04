from functools import partial
import json
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, Request

from src.app.middlewares.auth_middleware import JWTAuth
from src.app.schemas.requests.auth import JWTClaims


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


async def get_jwt_claims(request: Request) -> JWTClaims:
    """Extract JWT claims from Kong headers and return as a structured object"""
    headers = request.headers

    # Parse list and dict headers with proper fallbacks
    try:
        system_permissions_str = headers.get("x-kong-jwt-claim-system_permissions", "[]")
        system_permissions = json.loads(system_permissions_str)
        if isinstance(system_permissions, dict) and not system_permissions:
            system_permissions = []
    except json.JSONDecodeError:
        system_permissions = []

    try:
        # Now expecting project_roles as Dict[str, List[str]]
        project_roles_str = headers.get("x-kong-jwt-claim-project_roles", "{}")
        project_roles = json.loads(project_roles_str)
        # Ensure values are lists
        project_roles = {k: (v if isinstance(v, list) else [v]) for k, v in project_roles.items()}
    except json.JSONDecodeError:
        project_roles = {}

    try:
        project_permissions = json.loads(headers.get("x-kong-jwt-claim-project_permissions", "{}"))
    except json.JSONDecodeError:
        project_permissions = {}

    # Convert string boolean to Python boolean
    is_jira_linked = headers.get("x-kong-jwt-claim-is_jira_linked", "").lower() == "true"

    return JWTClaims(
        sub=headers.get("x-kong-jwt-claim-sub", ""),
        email=headers.get("x-kong-jwt-claim-email", ""),
        name=headers.get("x-kong-jwt-claim-name", ""),
        system_role=headers.get("x-kong-jwt-claim-system_role", ""),
        system_permissions=system_permissions,
        project_roles=project_roles,
        project_permissions=project_permissions,
        is_jira_linked=is_jira_linked,
        exp=int(headers.get("x-kong-jwt-claim-exp", 0)),
        iat=int(headers.get("x-kong-jwt-claim-iat", 0)),
        iss=headers.get("x-kong-jwt-claim-iss", "")
    )
