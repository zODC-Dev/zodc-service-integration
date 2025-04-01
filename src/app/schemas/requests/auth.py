from typing import Dict, List

from pydantic import BaseModel


class JWTClaims(BaseModel):
    sub: str
    email: str
    name: str
    system_role: str
    system_permissions: List[str]
    project_roles: Dict[str, List[str]]
    project_permissions: Dict[str, List[str]]
    is_jira_linked: bool
    exp: int
    iat: int
    iss: str
