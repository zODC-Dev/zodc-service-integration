from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer

security = HTTPBearer()


class JWTAuth:
    def __init__(
        self,
        required_system_roles: Optional[List[str]] = None,
        required_project_roles: Optional[List[str]] = None,
        required_permissions: Optional[List[str]] = None,
        require_all_roles: bool = False
    ):
        """Initialize JWTAuth middleware

        Args:
            required_system_roles: List of required system roles
            required_project_roles: List of required project roles
            required_permissions: List of required permissions
            require_all_roles: If True, user must have all required roles
        """
        self.required_system_roles = required_system_roles or []
        self.required_project_roles = required_project_roles or []
        self.required_permissions = required_permissions or []
        self.require_all_roles = require_all_roles

    def _get_project_id(self, request: Request) -> Optional[str]:
        """Extract project ID from request path parameters"""
        try:
            return str(request.path_params.get("project_id"))
        except (KeyError, ValueError):
            return None

    def _check_project_roles(self, payload: Dict[str, Any], request: Request) -> bool:
        """Check if user has required project roles"""
        project_id = self._get_project_id(request)
        if not project_id:
            return False

        user_project_roles = payload.get("project_roles", {})
        project_roles = user_project_roles.get(str(project_id), [])  # Now expecting a list of roles

        if not project_roles:
            return False

        if self.require_all_roles:
            return all(role in project_roles for role in self.required_project_roles)
        return any(role in project_roles for role in self.required_project_roles)

    def _check_system_roles(self, payload: Dict[str, Any]) -> bool:
        """Check if user has required system roles"""
        if not self.required_system_roles:
            return True

        user_system_role = payload.get("system_role")
        if not user_system_role:
            return False

        return user_system_role in self.required_system_roles

    def _check_permissions(self, payload: Dict[str, Any]) -> bool:
        """Check if user has required permissions"""
        if not self.required_permissions:
            return True

        user_permissions = payload.get("system_permissions", [])
        if not user_permissions:
            return False

        if self.require_all_roles:
            return all(perm in user_permissions for perm in self.required_permissions)
        return any(perm in user_permissions for perm in self.required_permissions)

    async def __call__(self, request: Request, token: Dict[str, Any]) -> Dict[str, Any]:
        """Validate token and check permissions"""
        if not self._check_system_roles(token):
            raise HTTPException(
                status_code=403,
                detail="Insufficient system role"
            )

        if self.required_project_roles and not self._check_project_roles(token, request):
            raise HTTPException(
                status_code=403,
                detail="Insufficient project role"
            )

        if not self._check_permissions(token):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        return token
