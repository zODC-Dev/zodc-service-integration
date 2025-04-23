from datetime import time
from typing import Optional

from fastapi import HTTPException

from src.app.schemas.requests.system_config import (
    SystemConfigCreateRequest,
    SystemConfigUpdateRequest,
)
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.system_config import (
    SystemConfigListResponse,
    SystemConfigResponse,
)
from src.app.services.system_config_service import SystemConfigApplicationService
from src.configs.logger import log
from src.domain.models.system_config import ConfigScope, ConfigType


class SystemConfigController:
    """Controller for system configuration APIs"""

    def __init__(self, system_config_service: SystemConfigApplicationService):
        self.system_config_service = system_config_service

    async def get_config(self, id: int) -> StandardResponse[SystemConfigResponse]:
        """Get configuration by ID"""
        try:
            config = await self.system_config_service.get_config(id)
            if not config:
                raise HTTPException(status_code=404, detail=f"Config with ID {id} not found")

            result = SystemConfigResponse(
                id=config.id,
                key=config.key,
                scope=config.scope,
                project_key=config.project_key,
                type=config.type,
                value=config.value,
                description=config.description,
                created_at=config.created_at,
                updated_at=config.updated_at
            )

            return StandardResponse(
                data=result,
                message="Configuration retrieved successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"Error getting config: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_config_by_key(self, key: str, scope: str = "global",
                                project_key: Optional[str] = None) -> StandardResponse[SystemConfigResponse]:
        """Get configuration by key, scope and project_key"""
        try:
            # Convert string scope to enum
            scope_enum = ConfigScope(scope)

            config = await self.system_config_service.get_config_by_key(key, scope_enum, project_key)
            if not config:
                raise HTTPException(status_code=404, detail=f"Config with key '{key}' not found")

            result = SystemConfigResponse(
                id=config.id,
                key=config.key,
                scope=config.scope,
                project_key=config.project_key,
                type=config.type,
                value=config.value,
                description=config.description,
                created_at=config.created_at,
                updated_at=config.updated_at
            )

            return StandardResponse(
                data=result,
                message="Configuration retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Invalid scope value: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid scope value: {str(e)}") from e
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"Error getting config by key: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def list_configs(self, scope: Optional[str] = None, project_key: Optional[str] = None,
                           limit: int = 100, offset: int = 0) -> StandardResponse[SystemConfigListResponse]:
        """List configurations with pagination"""
        try:
            # Convert string scope to enum if provided
            scope_enum = None
            if scope:
                scope_enum = ConfigScope(scope)

            configs = await self.system_config_service.list_configs(scope_enum, project_key, limit, offset)

            # Convert domain models to response objects
            items = []
            for config in configs:
                items.append(SystemConfigResponse(
                    id=config.id,
                    key=config.key,
                    scope=config.scope,
                    project_key=config.project_key,
                    type=config.type,
                    value=config.value,
                    description=config.description,
                    created_at=config.created_at,
                    updated_at=config.updated_at
                ))

            result = SystemConfigListResponse(
                items=items,
                total=len(items),  # In a real app, should get a count from DB
                limit=limit,
                offset=offset
            )

            return StandardResponse(
                data=result,
                message="Configurations retrieved successfully"
            )
        except ValueError as e:
            log.error(f"Invalid scope value: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid scope value: {str(e)}") from e
        except Exception as e:
            log.error(f"Error listing configs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def create_config(self, data: SystemConfigCreateRequest) -> StandardResponse[SystemConfigResponse]:
        """Create a new configuration"""
        try:
            # Get the value based on the type
            value = None
            if data.type.value == ConfigType.INT.value:
                value = data.int_value
            elif data.type.value == ConfigType.FLOAT.value:
                value = data.float_value
            elif data.type.value == ConfigType.STRING.value:
                value = data.string_value
            elif data.type.value == ConfigType.BOOL.value:
                value = data.bool_value
            elif data.type.value == ConfigType.TIME.value:
                # Convert string to time object
                if isinstance(data.time_value, str):
                    parts = data.time_value.split(":")
                    if len(parts) == 2:
                        value = time(int(parts[0]), int(parts[1]))
                    elif len(parts) == 3:
                        value = time(int(parts[0]), int(parts[1]), int(parts[2]))

            if value is None:
                raise HTTPException(status_code=400, detail=f"Value for type {data.type} is required")

            config = await self.system_config_service.create_config(
                key=data.key,
                value=value,
                scope=data.scope,
                project_key=data.project_key,
                description=data.description
            )

            result = SystemConfigResponse(
                id=config.id,
                key=config.key,
                scope=config.scope,
                project_key=config.project_key,
                type=config.type,
                value=config.value,
                description=config.description,
                created_at=config.created_at,
                updated_at=config.updated_at
            )

            return StandardResponse(
                data=result,
                message="Configuration created successfully"
            )
        except ValueError as e:
            log.error(f"Invalid input data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
        except Exception as e:
            log.error(f"Error creating config: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def update_config(self, id: int, data: SystemConfigUpdateRequest) -> StandardResponse[SystemConfigResponse]:
        """Update an existing configuration"""
        try:
            # First check if config exists
            existing = await self.system_config_service.get_config(id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Config with ID {id} not found")

            # Prepare update parameters
            update_params = {}

            if data.key is not None:
                update_params["key"] = data.key

            if data.scope is not None:
                update_params["scope"] = data.scope

            if data.project_key is not None:
                update_params["project_key"] = data.project_key

            if data.description is not None:
                update_params["description"] = data.description

            # Handle value based on type
            if data.type is not None:
                value = None
                if data.type.value == ConfigType.INT.value and data.int_value is not None:
                    value = data.int_value
                elif data.type.value == ConfigType.FLOAT.value and data.float_value is not None:
                    value = data.float_value
                elif data.type.value == ConfigType.STRING.value and data.string_value is not None:
                    value = data.string_value
                elif data.type.value == ConfigType.BOOL.value and data.bool_value is not None:
                    value = data.bool_value
                elif data.type.value == ConfigType.TIME.value and data.time_value is not None:
                    # Convert string to time object
                    parts = data.time_value.split(":")
                    if len(parts) == 2:
                        value = time(int(parts[0]), int(parts[1]))
                    elif len(parts) == 3:
                        value = time(int(parts[0]), int(parts[1]), int(parts[2]))

                if value is not None:
                    update_params["value"] = value

            # Update if we have any parameters
            if update_params:
                config = await self.system_config_service.update_config(id, **update_params)

                result = SystemConfigResponse(
                    id=config.id,
                    key=config.key,
                    scope=config.scope,
                    project_key=config.project_key,
                    type=config.type,
                    value=config.value,
                    description=config.description,
                    created_at=config.created_at,
                    updated_at=config.updated_at
                )

                return StandardResponse(
                    data=result,
                    message="Configuration updated successfully"
                )
            else:
                # No updates provided
                raise HTTPException(status_code=400, detail="No update parameters provided")
        except HTTPException:
            raise
        except ValueError as e:
            log.error(f"Invalid input data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
        except Exception as e:
            log.error(f"Error updating config: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def delete_config(self, id: int) -> StandardResponse[bool]:
        """Delete a configuration"""
        try:
            # Check if config exists
            existing = await self.system_config_service.get_config(id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Config with ID {id} not found")

            result = await self.system_config_service.delete_config(id)

            return StandardResponse(
                data=result,
                message="Configuration deleted successfully"
            )
        except HTTPException:
            raise
        except Exception as e:
            log.error(f"Error deleting config: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def get_project_configs(self, project_key: str) -> StandardResponse[SystemConfigListResponse]:
        """Get all configurations for a project, including global fallbacks"""
        try:
            # Get project-specific configs
            project_configs = await self.system_config_service.list_configs(
                scope=ConfigScope.PROJECT,
                project_key=project_key
            )

            # Get global configs
            global_configs = await self.system_config_service.list_configs(
                scope=ConfigScope.GLOBAL
            )

            # Create a dictionary of configs by key
            configs_dict = {}

            # First add all global configs
            for config in global_configs:
                configs_dict[config.key] = config

            # Then override with project-specific configs
            for config in project_configs:
                configs_dict[config.key] = config

            # Convert to response objects
            items = []
            for config in configs_dict.values():
                items.append(SystemConfigResponse(
                    id=config.id,
                    key=config.key,
                    scope=config.scope,
                    project_key=config.project_key,
                    type=config.type,
                    value=config.value,
                    description=config.description,
                    created_at=config.created_at,
                    updated_at=config.updated_at
                ))

            result = SystemConfigListResponse(
                items=items,
                total=len(items),
                limit=len(items),
                offset=0
            )

            return StandardResponse(
                data=result,
                message=f"Configurations for project {project_key} retrieved successfully"
            )
        except Exception as e:
            log.error(f"Error getting project configs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e
