from datetime import time
from typing import List, Optional, Union

from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.database import log
from src.domain.constants.system_config import SystemConfigConstants
from src.domain.models.database.system_config import (
    ProjectConfigDBCreateDTO,
    ProjectConfigDBUpdateDTO,
    SystemConfigDBCreateDTO,
    SystemConfigDBUpdateDTO,
)
from src.domain.models.system_config import ConfigScope, ConfigType, ProjectConfigModel, SystemConfigModel
from src.domain.repositories.system_config_repository import ISystemConfigRepository


class SystemConfigApplicationService:
    """Service for system configuration management"""

    def __init__(self, system_config_repository: ISystemConfigRepository):
        self.system_config_repository = system_config_repository

    async def get_config(self, session: AsyncSession, id: int) -> Optional[SystemConfigModel]:
        """Get a configuration by ID"""
        return await self.system_config_repository.get(session=session, id=id)

    async def get_config_by_key_and_project_key(self, session: AsyncSession, key: str, project_key: str) -> Optional[SystemConfigModel]:
        """Get a configuration by key and project_key"""
        return await self.system_config_repository.get_by_key_for_project(session=session, key=key, project_key=project_key)

    async def get_config_by_key(self, session: AsyncSession, key: str, scope: ConfigScope = ConfigScope.GENERAL) -> Optional[SystemConfigModel]:
        """Get a configuration by key and scope"""
        return await self.system_config_repository.get_by_key(session=session, key=key, scope=scope)

    async def list_configs(self, session: AsyncSession, scope: Optional[ConfigScope] = None,
                           limit: int = 100, offset: int = 0,
                           search: Optional[str] = None,
                           sort_by: Optional[str] = None,
                           sort_order: Optional[str] = None) -> tuple[List[SystemConfigModel], int]:
        """List configurations with pagination, search, and sorting"""
        return await self.system_config_repository.list(
            session=session,
            scope=scope,
            limit=limit,
            offset=offset,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )

    async def list_project_configs(self, session: AsyncSession, project_key: str,
                                   limit: int = 100, offset: int = 0) -> tuple[List[SystemConfigModel], int]:
        """List configurations for a specific project"""
        return await self.system_config_repository.list_for_project(
            session=session,
            project_key=project_key,
            limit=limit,
            offset=offset
        )

    async def create_config(self, session: AsyncSession, key: str, value: Union[int, float, str, bool, time],
                            scope: ConfigScope = ConfigScope.GENERAL,
                            description: Optional[str] = None) -> SystemConfigModel:
        """Create a new configuration"""
        # Determine the type based on value
        config_type = None
        if isinstance(value, int):
            config_type = ConfigType.INT
            dto = SystemConfigDBCreateDTO(
                key=key,
                scope=scope,
                type=config_type,
                int_value=value,
                description=description
            )
        elif isinstance(value, float):
            config_type = ConfigType.FLOAT
            dto = SystemConfigDBCreateDTO(
                key=key,
                scope=scope,
                type=config_type,
                float_value=value,
                description=description
            )
        elif isinstance(value, str):
            config_type = ConfigType.STRING
            dto = SystemConfigDBCreateDTO(
                key=key,
                scope=scope,
                type=config_type,
                string_value=value,
                description=description
            )
        elif isinstance(value, bool):
            config_type = ConfigType.BOOL
            dto = SystemConfigDBCreateDTO(
                key=key,
                scope=scope,
                type=config_type,
                bool_value=value,
                description=description
            )
        elif isinstance(value, time):
            config_type = ConfigType.TIME
            dto = SystemConfigDBCreateDTO(
                key=key,
                scope=scope,
                type=config_type,
                time_value=value,
                description=description
            )
        else:
            raise ValueError(f"Unsupported value type: {type(value)}")

        return await self.system_config_repository.create(session=session, dto=dto)

    async def create_project_config(self, session: AsyncSession, system_config_id: int, project_key: str,
                                    value: Union[int, float, str, bool, time]) -> ProjectConfigModel:
        """Create a project-specific configuration"""
        # Get the system config to determine type
        system_config = await self.get_config(session=session, id=system_config_id)
        if not system_config:
            raise ValueError(f"System config with ID {system_config_id} not found")

        # Create the appropriate DTO based on type
        if system_config.type == ConfigType.INT and isinstance(value, int):
            dto = ProjectConfigDBCreateDTO(
                system_config_id=system_config_id,
                project_key=project_key,
                int_value=value
            )
        elif system_config.type == ConfigType.FLOAT and isinstance(value, (int, float)):
            dto = ProjectConfigDBCreateDTO(
                system_config_id=system_config_id,
                project_key=project_key,
                float_value=value
            )
        elif system_config.type == ConfigType.STRING and isinstance(value, str):
            dto = ProjectConfigDBCreateDTO(
                system_config_id=system_config_id,
                project_key=project_key,
                string_value=value
            )
        elif system_config.type == ConfigType.BOOL and isinstance(value, bool):
            dto = ProjectConfigDBCreateDTO(
                system_config_id=system_config_id,
                project_key=project_key,
                bool_value=value
            )
        elif system_config.type == ConfigType.TIME and isinstance(value, time):
            dto = ProjectConfigDBCreateDTO(
                system_config_id=system_config_id,
                project_key=project_key,
                time_value=value
            )
        else:
            raise ValueError(f"Value type doesn't match config type: {system_config.type}")

        return await self.system_config_repository.create_project_config(session=session, dto=dto)

    async def update_config(self, session: AsyncSession, id: int, type: Optional[ConfigType] = None,
                            scope: Optional[ConfigScope] = None,
                            value: Optional[Union[int, float, str, bool, time]] = None,
                            description: Optional[str] = None) -> Optional[SystemConfigModel]:
        """Update an existing configuration"""
        # Create DTO with initial values
        dto = SystemConfigDBUpdateDTO(
            description=description
        )

        # If value is provided, set the appropriate field based on type
        if value is not None:
            dto.type = type
            dto.scope = scope

            config_type = type

            # If type is not provided, get it from the existing config
            if config_type is None:
                existing = await self.get_config(session=session, id=id)
                if not existing:
                    return None
                config_type = existing.type

            # Set the appropriate value field based on type
            if config_type == ConfigType.INT and isinstance(value, int):
                dto.int_value = value
            elif config_type == ConfigType.FLOAT and isinstance(value, (int, float)):
                dto.float_value = value
            elif config_type == ConfigType.STRING and isinstance(value, str):
                dto.string_value = value
            elif config_type == ConfigType.BOOL and isinstance(value, bool):
                dto.bool_value = value
            elif config_type == ConfigType.TIME and isinstance(value, time):
                dto.time_value = value
            else:
                raise ValueError(f"Value type doesn't match config type: {config_type}")

        return await self.system_config_repository.update(session=session, id=id, dto=dto)

    async def update_project_config(self, session: AsyncSession, id: int,
                                    value: Union[int, float, str, bool, time],
                                    value_type: ConfigType = ConfigType.STRING) -> Optional[ProjectConfigModel]:
        """Update a project-specific configuration"""
        # Get the existing project config to determine the system config type
        project_config = await self.system_config_repository.get_project_config_by_id(session=session, id=id)
        log.info(f"project_config: {project_config}")
        if not project_config:
            raise ValueError(f"Project config with ID {id} not found")

        # Create DTO with the appropriate value field
        dto = ProjectConfigDBUpdateDTO(
            project_key=project_config.project_key,
            system_config_id=project_config.system_config_id,
        )

        # Set the appropriate value field based on system config type
        config_type = value_type
        if config_type == ConfigType.INT and isinstance(value, int):
            dto.int_value = value
        elif config_type == ConfigType.FLOAT and isinstance(value, (int, float)):
            dto.float_value = value
        elif config_type == ConfigType.STRING and isinstance(value, str):
            dto.string_value = value
        elif config_type == ConfigType.BOOL and isinstance(value, bool):
            dto.bool_value = value
        elif config_type == ConfigType.TIME and isinstance(value, time):
            dto.time_value = value
        else:
            raise ValueError(f"Value type doesn't match config type: {config_type}")

        log.info(f"dto: {dto}")

        return await self.system_config_repository.update_project_config(session=session, id=id, dto=dto)

    async def delete_config(self, session: AsyncSession, id: int) -> bool:
        """Delete a configuration"""
        return await self.system_config_repository.delete(session=session, id=id)

    async def delete_project_config(self, session: AsyncSession, id: int) -> bool:
        """Delete a project-specific configuration"""
        return await self.system_config_repository.delete_project_config(session=session, id=id)

    async def get_working_hours_per_day(self, session: AsyncSession) -> int:
        """Get working_hours_per_day config with fallback to default value"""
        key = SystemConfigConstants.WORKING_HOURS_PER_DAY
        config = await self.get_config_by_key(session=session, key=key, scope=ConfigScope.GENERAL)

        return config.value if config else 8  # Default: 8 hours

    async def get_estimate_point_to_hours(self, session: AsyncSession, project_key: Optional[str] = None) -> int:
        """Get estimate_point_to_hours config with fallback to default value"""
        key = SystemConfigConstants.ESTIMATE_POINT_TO_HOURS

        if project_key:
            # Try to get project-specific value
            config = await self.get_config_by_key_and_project_key(session=session, key=key, project_key=project_key)
        else:
            # Get general config
            config = await self.get_config_by_key(session=session, key=key, scope=ConfigScope.GENERAL)

        return config.value if config else 4  # Default: 4 hours

    async def get_lunch_break_minutes(self, session: AsyncSession) -> int:
        """Get lunch_break_minutes config with fallback to default value"""
        key = SystemConfigConstants.LUNCH_BREAK_MINUTES
        config = await self.get_config_by_key(session=session, key=key, scope=ConfigScope.GENERAL)

        return config.value if config else 30  # Default: 30 minutes

    async def get_lunch_break_start_time(self, session: AsyncSession) -> time:
        """Get lunch_break_start_time config with fallback to default value"""
        key = SystemConfigConstants.LUNCH_BREAK_START_TIME
        config = await self.get_config_by_key(session=session, key=key, scope=ConfigScope.GENERAL)

        return config.value if config else time(12, 30)  # Default: 12:30 PM

    async def get_lunch_break_end_time(self, session: AsyncSession) -> time:
        """Get lunch_break_end_time config with fallback to default value"""
        key = SystemConfigConstants.LUNCH_BREAK_END_TIME
        config = await self.get_config_by_key(session=session, key=key, scope=ConfigScope.GENERAL)

        return config.value if config else time(13, 0)  # Default: 1:00 PM

    async def get_start_work_hour(self, session: AsyncSession) -> time:
        """Get start_work_hour config with fallback to default value"""
        key = SystemConfigConstants.START_WORK_HOUR
        config = await self.get_config_by_key(session=session, key=key, scope=ConfigScope.GENERAL)

        return config.value if config else time(8, 30)  # Default: 8:30 AM

    async def get_end_work_hour(self, session: AsyncSession) -> time:
        """Get end_work_hour config with fallback to default value"""
        key = SystemConfigConstants.END_WORK_HOUR
        config = await self.get_config_by_key(session=session, key=key, scope=ConfigScope.GENERAL)

        return config.value if config else time(17, 0)  # Default: 5:00 PM

    async def get_project_config(self, session: AsyncSession, id: int) -> Optional[ProjectConfigModel]:
        """Get a project-specific configuration by ID"""
        try:
            return await self.system_config_repository.get_project_config_by_id(session=session, id=id)
        except Exception:
            # If the method doesn't exist in the repository, let's implement it here
            # This is temporary until we update the repository
            result = None

            # Get all configs and search for the project config with this ID
            configs, _ = await self.list_configs(session=session)
            for config in configs:
                for pc in config.project_configs:
                    if pc.id == id:
                        result = pc
                        break
                if result:
                    break

            return result
