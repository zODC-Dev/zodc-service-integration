from typing import Optional, List
from pydantic import BaseModel

class PermissionVerificationRequest(BaseModel):
    token: str
    user_id: int
    project_id: Optional[int] = None
    scope: str
    permissions: List[str]

class PermissionVerificationResponse(BaseModel):
    allowed: bool
    user_id: int
    permissions: List[str]
    scope: str
    project_id: Optional[int] = None
    error: Optional[str] = None 