from datetime import time
from enum import Enum
from typing import Optional, Union

from src.domain.models.base import BaseModel


class ConfigScope(str, Enum):
    """Scope of configuration"""
    GLOBAL = "global"
    PROJECT = "project"


class ConfigType(str, Enum):
    """Type of configuration value"""
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    TIME = "time"


class SystemConfigModel(BaseModel):
    """Model for system configuration"""
    id: Optional[int] = None
    key: str
    scope: ConfigScope
    project_key: Optional[str] = None
    type: ConfigType
    value: Union[int, float, str, bool, time, None] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def get_value_for_type(self) -> Union[int, float, str, bool, time, None]:
        """Returns the value based on the config type"""
        return self.value

    @classmethod
    def create_from_value(cls, key: str, value: Union[int, float, str, bool, time],
                          scope: ConfigScope = ConfigScope.GLOBAL,
                          project_key: Optional[str] = None,
                          description: Optional[str] = None) -> 'SystemConfigModel':
        """Create a config model from a value, automatically determining the type"""
        config_type = None
        if isinstance(value, int):
            config_type = ConfigType.INT
        elif isinstance(value, float):
            config_type = ConfigType.FLOAT
        elif isinstance(value, str):
            config_type = ConfigType.STRING
        elif isinstance(value, bool):
            config_type = ConfigType.BOOL
        elif isinstance(value, time):
            config_type = ConfigType.TIME
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

        return cls(
            key=key,
            scope=scope,
            project_key=project_key,
            type=config_type,
            value=value,
            description=description
        )
