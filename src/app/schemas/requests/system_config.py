from datetime import time
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic.alias_generators import to_camel


class ConfigScopeEnum(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"


class ConfigTypeEnum(str, Enum):
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    TIME = "time"


class ConfigValueTypeBase(BaseModel):
    type: ConfigTypeEnum
    description: Optional[str] = None


class IntConfigRequest(ConfigValueTypeBase):
    type: ConfigTypeEnum = ConfigTypeEnum.INT
    value: int


class FloatConfigRequest(ConfigValueTypeBase):
    type: ConfigTypeEnum = ConfigTypeEnum.FLOAT
    value: float


class StringConfigRequest(ConfigValueTypeBase):
    type: ConfigTypeEnum = ConfigTypeEnum.STRING
    value: str


class BoolConfigRequest(ConfigValueTypeBase):
    type: ConfigTypeEnum = ConfigTypeEnum.BOOL
    value: bool


class TimeConfigRequest(ConfigValueTypeBase):
    type: ConfigTypeEnum = ConfigTypeEnum.TIME
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
    scope: ConfigScopeEnum = ConfigScopeEnum.GLOBAL
    project_key: Optional[str] = None
    type: ConfigTypeEnum
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
        if values.get('scope') == ConfigScopeEnum.PROJECT and not v:
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
        if field_name == 'int_value' and config_type == ConfigTypeEnum.INT and v is None:
            raise ValueError("int_value must be provided when type is 'int'")
        elif field_name == 'float_value' and config_type == ConfigTypeEnum.FLOAT and v is None:
            raise ValueError("float_value must be provided when type is 'float'")
        elif field_name == 'string_value' and config_type == ConfigTypeEnum.STRING and v is None:
            raise ValueError("string_value must be provided when type is 'string'")
        elif field_name == 'bool_value' and config_type == ConfigTypeEnum.BOOL and v is None:
            raise ValueError("bool_value must be provided when type is 'bool'")
        elif field_name == 'time_value' and config_type == ConfigTypeEnum.TIME and v is None:
            raise ValueError("time_value must be provided when type is 'time'")

        return v


class SystemConfigUpdateRequest(BaseModel):
    key: Optional[str] = Field(None, min_length=1, max_length=100)
    scope: Optional[ConfigScopeEnum] = None
    project_key: Optional[str] = None
    type: Optional[ConfigTypeEnum] = None
    int_value: Optional[int] = None
    float_value: Optional[float] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None
    time_value: Optional[str] = None  # Format HH:MM:SS or HH:MM
    description: Optional[str] = None

    class Config:
        populate_by_name = True
        alias_generator = to_camel
