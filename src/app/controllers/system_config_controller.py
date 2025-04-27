from datetime import time
from typing import List, Optional, Union

from fastapi import HTTPException

from src.app.schemas.requests.system_config import (
    SystemConfigCreateRequest,
    SystemConfigPatchRequest,
    SystemConfigUpdateRequest,
)
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.system_config import (
    ProjectConfigResponse,
    SystemConfigListResponse,
    SystemConfigResponse,
)
from src.app.services.system_config_service import SystemConfigApplicationService
from src.configs.logger import log
from src.domain.models.system_config import ConfigScope, ConfigType, ProjectConfigModel


class SystemConfigController:
    """Controller for system configuration APIs"""

    def __init__(self, system_config_service: SystemConfigApplicationService):
        self.system_config_service = system_config_service

    async def list_scopes(self) -> StandardResponse[List[str]]:
        """List all scopes"""
        scopes = [scope.value for scope in ConfigScope]
        return StandardResponse(
            data=scopes,
            message="Scopes retrieved successfully"
        )

    async def get_config_by_key_and_project_key(self, key: str, project_key: str) -> StandardResponse[SystemConfigResponse]:
        """Get configuration by key and project key"""
        config = await self.system_config_service.get_config_by_key_and_project_key(key, project_key)
        if not config:
            raise HTTPException(
                status_code=404, detail=f"Config with key '{key}' and project key '{project_key}' not found")

        result = SystemConfigResponse(
            id=config.id,
            key=config.key,
            scope=config.scope,
            type=config.type,
            value=config.value,
            description=config.description,
            created_at=config.created_at,
            updated_at=config.updated_at,
            project_configs=[self._to_project_config_response(pc) for pc in config.project_configs]
        )

        return StandardResponse(
            data=result,
            message="Configuration retrieved successfully"
        )

    def _to_project_config_response(self, project_config: ProjectConfigModel) -> ProjectConfigResponse:
        """Convert domain project config model to response DTO"""
        return ProjectConfigResponse(
            id=project_config.id,
            project_key=project_config.project_key,
            system_config_id=project_config.system_config_id,
            value=project_config.value,
            created_at=project_config.created_at,
            updated_at=project_config.updated_at
        )

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
                type=config.type,
                value=config.value,
                description=config.description,
                created_at=config.created_at,
                updated_at=config.updated_at,
                project_configs=[self._to_project_config_response(pc) for pc in config.project_configs]
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

    async def get_config_by_key(self, key: str, scope: str = "general",
                                project_key: Optional[str] = None) -> StandardResponse[SystemConfigResponse]:
        """Get configuration by key, scope and optional project_key"""
        try:
            # Convert string scope to enum
            scope_enum = ConfigScope(scope)

            if project_key and scope_enum == ConfigScope.PROJECT:
                # Get project-specific config
                config = await self.system_config_service.get_config_by_key_and_project_key(key, project_key)
            else:
                # Get general config
                config = await self.system_config_service.get_config_by_key(key, scope_enum)

            if not config:
                raise HTTPException(status_code=404, detail=f"Config with key '{key}' not found")

            result = SystemConfigResponse(
                id=config.id,
                key=config.key,
                scope=config.scope,
                type=config.type,
                value=config.value,
                description=config.description,
                created_at=config.created_at,
                updated_at=config.updated_at,
                project_configs=[self._to_project_config_response(pc) for pc in config.project_configs]
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
                           page: int = 1, page_size: int = 10, search: Optional[str] = None,
                           sort_by: Optional[str] = None,
                           sort_order: Optional[str] = None) -> StandardResponse[SystemConfigListResponse]:
        """List configurations with pagination, search, and sorting"""
        try:
            # Convert string scope to enum if provided
            scope_enum = None
            if scope:
                scope_enum = ConfigScope(scope)

            # Calculate offset from page parameters
            offset = (page - 1) * page_size
            limit = page_size

            # Determine if we should use project-specific list
            if project_key:
                configs, total_count = await self.system_config_service.list_project_configs(
                    project_key=project_key,
                    limit=limit,
                    offset=offset
                )
            else:
                configs, total_count = await self.system_config_service.list_configs(
                    scope=scope_enum,
                    limit=limit,
                    offset=offset,
                    search=search,
                    sort_by=sort_by,
                    sort_order=sort_order
                )

            # Convert domain models to response objects
            items = []
            for config in configs:
                items.append(SystemConfigResponse(
                    id=config.id,
                    key=config.key,
                    scope=config.scope,
                    type=config.type,
                    value=config.value,
                    description=config.description,
                    created_at=config.created_at,
                    updated_at=config.updated_at,
                    project_configs=[self._to_project_config_response(pc) for pc in config.project_configs]
                ))

            # Calculate total pages
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

            result = SystemConfigListResponse(
                items=items,
                total=total_count,
                page=page,
                page_size=page_size,
                total_pages=total_pages
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
        """Create a new system configuration"""
        try:
            # Get the value based on the type
            value: Optional[Union[int, float, str, bool, time]] = None
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

            # First create the config
            config = await self.system_config_service.create_config(
                key=data.key,
                value=value,
                scope=data.scope,
                description=data.description
            )

            assert config.id is not None, "Config ID is required"
            # If scope is PROJECT and project_key is provided, create project-specific value
            if data.scope == ConfigScope.PROJECT and data.project_key:
                await self.system_config_service.create_project_config(
                    system_config_id=config.id,
                    project_key=data.project_key,
                    value=value
                )

            config = await self.system_config_service.get_config(config.id)

            result = SystemConfigResponse(
                id=config.id,
                key=config.key,
                scope=config.scope,
                type=config.type,
                value=config.value,
                description=config.description,
                created_at=config.created_at,
                updated_at=config.updated_at,
                project_configs=[self._to_project_config_response(pc) for pc in config.project_configs]
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

            # Get the value based on type
            value: Optional[Union[int, float, str, bool, time]] = None
            if data.type:
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

            # Update the config
            updated_config = await self.system_config_service.update_config(
                id=id,
                type=data.type,
                scope=data.scope,
                value=value,
                description=data.description
            )

            # If project_key is provided and scope is PROJECT, update or create project config
            if data.project_key and (data.scope == ConfigScope.PROJECT or existing.scope == ConfigScope.PROJECT):
                # Check if there's already a project config for this project
                existing_project_config = None
                for pc in updated_config.project_configs:
                    if pc.project_key == data.project_key:
                        existing_project_config = pc
                        break

                if existing_project_config:
                    # Update existing project config
                    if value is not None:
                        await self.system_config_service.update_project_config(
                            existing_project_config.id,
                            value=value
                        )
                else:
                    # Create new project config
                    if value is not None:
                        await self.system_config_service.create_project_config(
                            system_config_id=id,
                            project_key=data.project_key,
                            value=value
                        )

                # Refresh config to include updated project configs
                updated_config = await self.system_config_service.get_config(id)

            result = SystemConfigResponse(
                id=updated_config.id,
                key=updated_config.key,
                scope=updated_config.scope,
                type=updated_config.type,
                value=updated_config.value,
                description=updated_config.description,
                created_at=updated_config.created_at,
                updated_at=updated_config.updated_at,
                project_configs=[self._to_project_config_response(pc) for pc in updated_config.project_configs]
            )

            return StandardResponse(
                data=result,
                message="Configuration updated successfully"
            )
        except HTTPException:
            raise
        except ValueError as e:
            log.error(f"Invalid input data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
        except Exception as e:
            log.error(f"Error updating config: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e

    async def patch_config(self, id: int, data: SystemConfigPatchRequest) -> StandardResponse[SystemConfigResponse]:
        """Patch a system configuration with simpler value field"""
        try:
            # First check if config exists
            existing = await self.system_config_service.get_config(id)
            if not existing:
                raise HTTPException(status_code=404, detail=f"Config with ID {id} not found")

            # Convert value based on the type
            value = data.value
            if data.type.value == ConfigType.TIME.value and isinstance(value, str):
                # Convert string to time object for time type
                parts = value.split(":")
                if len(parts) == 2:
                    value = time(int(parts[0]), int(parts[1]))
                elif len(parts) == 3:
                    value = time(int(parts[0]), int(parts[1]), int(parts[2]))

            # Update the config with the new value
            if data.project_key and (data.scope == ConfigScope.PROJECT or existing.scope == ConfigScope.PROJECT):
                updated_config = await self.system_config_service.update_config(
                    id=id,
                    description=data.description
                )
                # Check if project config already exists
                existing_project_config = None
                for pc in updated_config.project_configs:
                    if pc.project_key == data.project_key:
                        existing_project_config = pc
                        break

                if existing_project_config and existing_project_config.id is not None:
                    # Update existing project config
                    await self.system_config_service.update_project_config(
                        existing_project_config.id,
                        value=value,
                        value_type=data.type
                    )
                else:
                    # Create new project config
                    await self.system_config_service.create_project_config(
                        system_config_id=id,
                        project_key=data.project_key,
                        value=value
                    )

                # Refresh config with updated project configs
                updated_config = await self.system_config_service.get_config(id)

                result = SystemConfigResponse(
                    id=updated_config.id,
                    key=updated_config.key,
                    scope=updated_config.scope,
                    type=updated_config.type,
                    value=updated_config.value,
                    description=updated_config.description,
                    created_at=updated_config.created_at,
                    updated_at=updated_config.updated_at,
                    project_configs=[self._to_project_config_response(pc) for pc in updated_config.project_configs]
                )
            else:
                updated_config = await self.system_config_service.update_config(
                    id=id,
                    description=data.description,
                    type=data.type,
                    scope=data.scope,
                    value=value
                )

                result = SystemConfigResponse(
                    id=updated_config.id,
                    key=updated_config.key,
                    scope=updated_config.scope,
                    type=updated_config.type,
                    value=updated_config.value,
                    description=updated_config.description,
                    created_at=updated_config.created_at,
                    updated_at=updated_config.updated_at,
                )

            return StandardResponse(
                data=result,
                message="Configuration patched successfully"
            )
        except ValueError as e:
            log.error(f"Invalid input data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid input: {str(e)}") from e
        except Exception as e:
            log.error(f"Error patching config: {str(e)}")
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
        """Get all configurations for a project"""
        try:
            # Get configs for the project
            configs, total_count = await self.system_config_service.list_project_configs(project_key)

            # Convert to response objects
            items = []
            for config in configs:
                items.append(SystemConfigResponse(
                    id=config.id,
                    key=config.key,
                    scope=config.scope,
                    type=config.type,
                    value=config.value,
                    description=config.description,
                    created_at=config.created_at,
                    updated_at=config.updated_at,
                    project_configs=[self._to_project_config_response(pc) for pc in config.project_configs]
                ))

            result = SystemConfigListResponse(
                items=items,
                total=total_count,
                page=1,
                page_size=len(items),
                total_pages=1
            )

            return StandardResponse(
                data=result,
                message=f"Configurations for project {project_key} retrieved successfully"
            )
        except Exception as e:
            log.error(f"Error getting project configs: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) from e
