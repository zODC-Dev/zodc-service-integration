from datetime import time
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic.alias_generators import to_camel

from src.domain.models.system_config import ConfigScope, ConfigType


class ConfigValueTypeBase(BaseModel):
    type: ConfigType
    description: Optional[str] = None


class IntConfigRequest(ConfigValueTypeBase):
    type: ConfigType = ConfigType.INT
    value: int


class FloatConfigRequest(ConfigValueTypeBase):
    type: ConfigType = ConfigType.FLOAT
    value: float


class StringConfigRequest(ConfigValueTypeBase):
    type: ConfigType = ConfigType.STRING
    value: str


class BoolConfigRequest(ConfigValueTypeBase):
    type: ConfigType = ConfigType.BOOL
    value: bool


class TimeConfigRequest(ConfigValueTypeBase):
    type: ConfigType = ConfigType.TIME
    value: str  # Format HH:MM:SS or HH:MM

    @field_validator('value')
    @classmethod
    def validate_time_format(cls, v):
        try:
            # Parse time string
            parts = v.split(':')
            if len(parts) == 2:
                hour, minute = parts
                return time(int(hour), int(minute))
            elif len(parts) == 3:
                hour, minute, second = parts
                return time(int(hour), int(minute), int(second))
            else:
                raise ValueError("Time must be in format HH:MM or HH:MM:SS")
        except Exception as e:
            raise ValueError(f"Invalid time format: {e}") from e


class SystemConfigCreateRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=100)
    scope: ConfigScope = ConfigScope.GENERAL
    project_key: Optional[str] = None
    type: ConfigType
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    time_value: Optional[str] = None  # Format HH:MM:SS or HH:MM
    description: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel

    @field_validator('project_key')
    @classmethod
    def validate_project_key(cls, v, info: Any):
        values = info.data
        if values.get('scope') == ConfigScope.PROJECT and not v:
            raise ValueError("project_key is required when scope is 'project'")
        return v

    @field_validator('int_value', 'float_value', 'string_value', 'bool_value', 'time_value')
    @classmethod
    def validate_value_matches_type(cls, v, info: Any):
        values = info.data
        if 'type' not in values:
            return v

        config_type = values['type']
        field_name = f"{config_type.value}_value"

        # Check that the value is provided for the right type
        if field_name == 'int_value' and config_type == ConfigType.INT and v is None:
            raise ValueError("int_value must be provided when type is 'int'")
        elif field_name == 'float_value' and config_type == ConfigType.FLOAT and v is None:
            raise ValueError("float_value must be provided when type is 'float'")
        elif field_name == 'string_value' and config_type == ConfigType.STRING and v is None:
            raise ValueError("string_value must be provided when type is 'string'")
        elif field_name == 'bool_value' and config_type == ConfigType.BOOL and v is None:
            raise ValueError("bool_value must be provided when type is 'bool'")
        elif field_name == 'time_value' and config_type == ConfigType.TIME and v is None:
            raise ValueError("time_value must be provided when type is 'time'")

        return v


class SystemConfigUpdateRequest(BaseModel):
    key: Optional[str] = Field(None, min_length=1, max_length=100)
    scope: Optional[ConfigScope] = None
    project_key: Optional[str] = None
    type: Optional[ConfigType] = None
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    time_value: Optional[str] = None  # Format HH:MM:SS or HH:MM
    description: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel


class SystemConfigPatchRequest(BaseModel):
    value: Any
    type: ConfigType
    scope: Optional[ConfigScope] = None
    project_key: Optional[str] = Field(None, description="Only used when scope is PROJECT", alias="projectKey")
    description: Optional[str] = None

    @field_validator('value')
    @classmethod
    def validate_value_type(cls, v, info: Any):
        config_type = info.data.get('type')
        if not config_type:
            return v

        if config_type == ConfigType.INT and not isinstance(v, int):
            raise ValueError("Value must be an integer when type is 'int'")
        elif config_type == ConfigType.FLOAT and not isinstance(v, (int, float)):
            raise ValueError("Value must be a number when type is 'float'")
        elif config_type == ConfigType.STRING and not isinstance(v, str):
            raise ValueError("Value must be a string when type is 'string'")
        elif config_type == ConfigType.BOOL and not isinstance(v, bool):
            raise ValueError("Value must be a boolean when type is 'bool'")
        elif config_type == ConfigType.TIME and not isinstance(v, str):
            # Time validation
            try:
                parts = v.split(':')
                if len(parts) == 2:
                    hour, minute = parts
                    time(int(hour), int(minute))
                elif len(parts) == 3:
                    hour, minute, second = parts
                    time(int(hour), int(minute), int(second))
                else:
                    raise ValueError("Time must be in format HH:MM or HH:MM:SS")
            except Exception as e:
                raise ValueError(f"Invalid time format: {e}") from e

        return v

    @field_validator('project_key')
    @classmethod
    def validate_project_key(cls, v, info: Any):
        values = info.data
        if values.get('scope') == ConfigScope.PROJECT and not v:
            raise ValueError("project_key is required when scope is 'project'")
        return v

    class Config:
        populate_by_name = True
        alias_generator = to_camel
