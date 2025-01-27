import json
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
        self.required_system_roles = required_system_roles or []
        self.required_project_roles = required_project_roles or []
        self.required_permissions = required_permissions or []
        self.require_all_roles = require_all_roles

    async def __call__(
        self,
        request: Request
    ):
        try:
            # Extract JWT claims from Kong headers
            payload = self._extract_jwt_claims(request)

            # Add user info to request state
            request.state.user = payload

            if not self._validate_access(payload, request):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )

            return payload

        except Exception as e:
            raise HTTPException(
                status_code=403,
                detail=str(e)
            ) from e

    def _extract_jwt_claims(self, request: Request) -> Dict[str, Any]:
        """Extract JWT claims from Kong headers"""
        headers = request.headers
        payload = {
            "sub": headers.get("x-kong-jwt-claim-sub"),
            "email": headers.get("x-kong-jwt-claim-email"),
            "name": headers.get("x-kong-jwt-claim-name"),
            "system_role": headers.get("x-kong-jwt-claim-system_role"),
            "system_permissions": self._parse_list_header(headers.get("x-kong-jwt-claim-system_permissions")),
            "project_roles": self._parse_dict_header(headers.get("x-kong-jwt-claim-project_roles")),
            "project_permissions": self._parse_nested_dict_header(headers.get("x-kong-jwt-claim-project_permissions"))
        }

        if not payload["sub"]:
            raise HTTPException(
                status_code=401,
                detail="Missing user information in token"
            )

        return payload

    def _validate_access(self, payload: Dict[str, Any], request: Request) -> bool:
        """Validate system roles, project roles and permissions"""
        # Check system roles if required
        if self.required_system_roles and not self._check_system_roles(payload):
            return False

        # Check project roles if required
        if self.required_project_roles and not self._check_project_roles(payload, request):
            return False

        # Check permissions if required
        if self.required_permissions and not self._check_permissions(payload):
            return False

        return True

    def _check_system_roles(self, payload: Dict[str, Any]) -> bool:
        """Check if user has required system roles"""
        user_system_role = payload.get("system_role")
        if not user_system_role:
            return False

        if self.require_all_roles:
            return all(role == user_system_role for role in self.required_system_roles)
        return user_system_role in self.required_system_roles

    def _check_project_roles(self, payload: Dict[str, Any], request: Request) -> bool:
        """Check if user has required project roles"""
        project_id = self._get_project_id(request)
        if not project_id:
            return False

        user_project_roles: Dict[int, str] = payload.get("project_roles", {})
        project_role: Optional[str] = user_project_roles.get(project_id)

        if not project_role:
            return False

        if self.require_all_roles:
            return all(role == project_role for role in self.required_project_roles)
        return project_role in self.required_project_roles

    def _check_project_permissions(self, payload: Dict[str, Any], request: Request) -> bool:
        """Check if user has required project permissions"""
        project_id = self._get_project_id(request)
        if not project_id:
            return False

        project_permissions: Dict[int, List[str]] = payload.get("project_permissions", {})
        user_project_permissions: List[str] = project_permissions.get(project_id, [])

        if not user_project_permissions:
            return False

        if self.required_permissions:
            return all(perm in user_project_permissions for perm in self.required_permissions)
        return any(perm in user_project_permissions for perm in self.required_permissions)

    def _check_permissions(self, payload: Dict[str, Any]) -> bool:
        """Check if user has required permissions"""
        user_permissions: List[str] = payload.get("system_permissions", [])

        if self.require_all_roles:
            return all(perm in user_permissions for perm in self.required_permissions)
        return any(perm in user_permissions for perm in self.required_permissions)

    def _get_project_id(self, request: Request) -> Optional[int]:
        """Extract project_id from request path parameters or query parameters"""
        project_id = (
            request.path_params.get("project_id") or
            request.query_params.get("project_id")
        )
        if not project_id:
            raise HTTPException(
                status_code=401,
                detail="Missing project_id in token"
            )
        return int(project_id)

    def _parse_list_header(self, header_value: Optional[str]) -> List[str]:
        """Parse comma-separated list from header"""
        if not header_value:
            return []
        return [item.strip() for item in header_value.split(",")]

    def _parse_dict_header(self, header_value: Optional[str]) -> Dict[str, str]:
        """Parse JSON dictionary from header"""
        if not header_value:
            return {}
        try:
            result = json.loads(header_value)
            return {str(key): value for key, value in result.items()}
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            ) from e

    def _parse_nested_dict_header(self, header_value: Optional[str]) -> Dict[str, List[str]]:
        """Parse JSON dictionary with list values from header"""
        if not header_value:
            return {}
        try:
            result = json.loads(header_value)
            return {str(key): value for key, value in result.items()}
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail="Invalid token"
            ) from e
