from datetime import time
from typing import List, Optional, Union

from src.app.schemas.requests.system_config import ConfigScopeEnum, ConfigTypeEnum
from src.app.schemas.responses.base import BaseResponse


class ProjectConfigResponse(BaseResponse):
    id: int
    project_key: str
    system_config_id: int
    value: Union[int, float, str, bool, time, None]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SystemConfigResponse(BaseResponse):
    id: int
    key: str
    scope: ConfigScopeEnum
    type: ConfigTypeEnum
    value: Union[int, float, str, bool, time, None]
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    project_configs: List[ProjectConfigResponse] = []


class SystemConfigListResponse(BaseResponse):
    items: List[SystemConfigResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
