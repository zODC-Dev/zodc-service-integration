from datetime import time
from typing import List, Optional, Union

from src.app.schemas.requests.system_config import ConfigScopeEnum, ConfigTypeEnum
from src.app.schemas.responses.base import BaseResponse


class SystemConfigResponse(BaseResponse):
    id: int
    key: str
    scope: ConfigScopeEnum
    project_key: Optional[str] = None
    type: ConfigTypeEnum
    value: Union[int, float, str, bool, time, None]
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SystemConfigListResponse(BaseResponse):
    items: List[SystemConfigResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
