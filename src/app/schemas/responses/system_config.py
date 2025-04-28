from datetime import time
from typing import List, Optional, Union

from src.app.schemas.responses.base import BaseResponse
from src.domain.models.system_config import ConfigScope, ConfigType


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
    scope: ConfigScope
    type: ConfigType
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
