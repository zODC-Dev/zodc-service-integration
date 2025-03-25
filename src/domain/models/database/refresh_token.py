from datetime import datetime

from pydantic import BaseModel

from src.domain.constants.refresh_tokens import TokenType


class RefreshTokenDBCreateDTO(BaseModel):
    """DTO for creating a new refresh token"""
    token: str
    user_id: int
    expires_at: datetime
    token_type: TokenType
