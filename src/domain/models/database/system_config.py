from datetime import time
from typing import List, Optional

from pydantic import BaseModel

from src.domain.models.system_config import ConfigScope, ConfigType


class SystemConfigDBCreateDTO(BaseModel):
    """DTO for creating a system configuration in the database"""
    key: str
    scope: ConfigScope
    type: ConfigType
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    time_value: Optional[time] = None
    description: Optional[str] = None


class SystemConfigDBUpdateDTO(BaseModel):
    """DTO for updating a system configuration in the database"""
    key: Optional[str] = None
    scope: Optional[ConfigScope] = None
    type: Optional[ConfigType] = None
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    time_value: Optional[time] = None
    description: Optional[str] = None


class ProjectConfigDBCreateDTO(BaseModel):
    """DTO for creating a project-specific configuration in the database"""
    project_key: str
    system_config_id: int
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    time_value: Optional[time] = None


class ProjectConfigDBUpdateDTO(BaseModel):
    """DTO for updating a project-specific configuration in the database"""
    project_key: Optional[str] = None
    system_config_id: Optional[int] = None
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    time_value: Optional[time] = None


class SystemConfigWithProjectsDTO(BaseModel):
    """DTO for system config with its project-specific configurations"""
    id: int
    key: str
    scope: ConfigScope
    type: ConfigType
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    time_value: Optional[time] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    project_configs: List["ProjectConfigDTO"] = []


class ProjectConfigDTO(BaseModel):
    """DTO for project-specific configuration"""
    id: int
    project_key: str
    system_config_id: int
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    time_value: Optional[time] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
