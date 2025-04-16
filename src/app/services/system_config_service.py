from datetime import time
from typing import List, Optional, Union

from src.domain.models.system_config import ConfigScope, ConfigType, SystemConfigModel
from src.domain.repositories.system_config_repository import ISystemConfigRepository


class SystemConfigApplicationService:
    """Service for system configuration management"""

    def __init__(self, system_config_repository: ISystemConfigRepository):
        self.system_config_repository = system_config_repository

    async def get_config(self, id: int) -> Optional[SystemConfigModel]:
        """Get a configuration by ID"""
        return await self.system_config_repository.get(id)

    async def get_config_by_key(self, key: str, scope: ConfigScope = ConfigScope.GLOBAL,
                                project_key: Optional[str] = None) -> Optional[SystemConfigModel]:
        """Get a configuration by key, scope and project_key"""
        return await self.system_config_repository.get_by_key(key, scope, project_key)

    async def get_project_config_or_fallback(self, key: str, project_key: str) -> Optional[SystemConfigModel]:
        """Get project-specific configuration if exists, otherwise fall back to global configuration"""
        return await self.system_config_repository.get_by_key_with_fallback(key, project_key)

    async def list_configs(self, scope: Optional[ConfigScope] = None,
                           project_key: Optional[str] = None,
                           limit: int = 100, offset: int = 0) -> List[SystemConfigModel]:
        """List configurations with pagination, optionally filtered by scope and project_key"""
        return await self.system_config_repository.list(scope, project_key, limit, offset)

    async def create_config(self, key: str, value: Union[int, float, str, bool, time],
                            scope: ConfigScope = ConfigScope.GLOBAL,
                            project_key: Optional[str] = None,
                            description: Optional[str] = None) -> SystemConfigModel:
        """Create a new configuration"""
        config = SystemConfigModel.create_from_value(
            key=key,
            value=value,
            scope=scope,
            project_key=project_key,
            description=description
        )
        return await self.system_config_repository.create(config)

    async def update_config(self, id: int, key: Optional[str] = None,
                            value: Optional[Union[int, float, str, bool, time]] = None,
                            scope: Optional[ConfigScope] = None,
                            project_key: Optional[str] = None,
                            description: Optional[str] = None) -> Optional[SystemConfigModel]:
        """Update an existing configuration"""
        config = await self.system_config_repository.get(id)
        if not config:
            return None

        # Update fields if provided
        if key is not None:
            config.key = key
        if scope is not None:
            config.scope = scope
        if project_key is not None:
            config.project_key = project_key
        if description is not None:
            config.description = description
        if value is not None:
            # Determine new type based on value type
            if isinstance(value, int):
                config.type = ConfigType.INT
            elif isinstance(value, float):
                config.type = ConfigType.FLOAT
            elif isinstance(value, str):
                config.type = ConfigType.STRING
            elif isinstance(value, bool):
                config.type = ConfigType.BOOL
            elif isinstance(value, time):
                config.type = ConfigType.TIME
            config.value = value

        return await self.system_config_repository.update(config)

    async def delete_config(self, id: int) -> bool:
        """Delete a configuration"""
        return await self.system_config_repository.delete(id)

    async def upsert_config(self, key: str, value: Union[int, float, str, bool, time],
                            scope: ConfigScope = ConfigScope.GLOBAL,
                            project_key: Optional[str] = None,
                            description: Optional[str] = None) -> SystemConfigModel:
        """Create or update a configuration based on key, scope and project_key"""
        config = SystemConfigModel.create_from_value(
            key=key,
            value=value,
            scope=scope,
            project_key=project_key,
            description=description
        )
        return await self.system_config_repository.upsert(config)

    async def bulk_upsert_configs(self, configs: List[SystemConfigModel]) -> List[SystemConfigModel]:
        """Bulk create or update configurations"""
        return await self.system_config_repository.bulk_upsert(configs)

    async def get_working_hours_per_day(self, project_key: Optional[str] = None) -> int:
        """Get working_hours_per_day config with fallback to default value"""
        key = "working_hours_per_day"
        if project_key:
            config = await self.get_project_config_or_fallback(key, project_key)
        else:
            config = await self.get_config_by_key(key)

        return config.value if config else 8  # Default: 8 hours

    async def get_hours_per_point(self, project_key: Optional[str] = None) -> int:
        """Get hours_per_point config with fallback to default value"""
        key = "hours_per_point"
        if project_key:
            config = await self.get_project_config_or_fallback(key, project_key)
        else:
            config = await self.get_config_by_key(key)

        return config.value if config else 4  # Default: 4 hours

    async def get_lunch_break_minutes(self, project_key: Optional[str] = None) -> int:
        """Get lunch_break_minutes config with fallback to default value"""
        key = "lunch_break_minutes"
        if project_key:
            config = await self.get_project_config_or_fallback(key, project_key)
        else:
            config = await self.get_config_by_key(key)

        return config.value if config else 30  # Default: 30 minutes

    async def get_include_weekends(self, project_key: Optional[str] = None) -> bool:
        """Get include_weekends config with fallback to default value"""
        key = "include_weekends"
        if project_key:
            config = await self.get_project_config_or_fallback(key, project_key)
        else:
            config = await self.get_config_by_key(key)

        return config.value if config else False  # Default: False

    async def get_start_work_hour(self, project_key: Optional[str] = None) -> time:
        """Get start_work_hour config with fallback to default value"""
        key = "start_work_hour"
        if project_key:
            config = await self.get_project_config_or_fallback(key, project_key)
        else:
            config = await self.get_config_by_key(key)

        return config.value if config else time(9, 0)  # Default: 9:00 AM

    async def get_end_work_hour(self, project_key: Optional[str] = None) -> time:
        """Get end_work_hour config with fallback to default value"""
        key = "end_work_hour"
        if project_key:
            config = await self.get_project_config_or_fallback(key, project_key)
        else:
            config = await self.get_config_by_key(key)

        return config.value if config else time(17, 30)  # Default: 5:30 PM
