from datetime import time
from typing import List, Optional, Union

from pydantic import BaseModel

from src.app.schemas.requests.system_config import ConfigScopeEnum, ConfigTypeEnum


class SystemConfigResponse(BaseModel):
    id: int
    key: str
    scope: ConfigScopeEnum
    project_key: Optional[str] = None
    type: ConfigTypeEnum
    value: Union[int, float, str, bool, time, None]
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SystemConfigListResponse(BaseModel):
    items: List[SystemConfigResponse]
    total: int
    offset: int
    limit: int
