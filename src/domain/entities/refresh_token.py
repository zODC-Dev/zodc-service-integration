from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, EmailStr, Field

from src.domain.constants.auth import TokenType


class UserCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class AuthToken(BaseModel):
    access_token: str
    expires_at: datetime
    token_type: str = "bearer"
    refresh_token: Optional[str] = None


class MicrosoftIdentity(BaseModel):
    email: str
    name: Optional[str]
    access_token: str
    expires_in: int
    refresh_token: Optional[str]
    scope: str


class SSOCredentials(BaseModel):
    code: str
    state: str
    code_verifier: str


class RefreshTokenEntity(BaseModel):
    token: str
    user_id: int
    expires_at: datetime
    is_revoked: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    token_type: TokenType


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class JiraIdentity(BaseModel):
    access_token: str
    refresh_token: Optional[str]
    expires_in: int
    scope: str


class CachedToken(BaseModel):
    """Model for cached tokens"""
    access_token: str
    expires_at: Union[float, datetime]  # Allow both float and datetime
    token_type: Union[TokenType, str]  # Allow both TokenType enum and string

    @property
    def is_expired(self) -> bool:
        """Check if token is expired"""
        if isinstance(self.expires_at, datetime):
            return datetime.now() > self.expires_at
        return datetime.now().timestamp() > self.expires_at

    class Config:
        """Pydantic config"""
        arbitrary_types_allowed = True
