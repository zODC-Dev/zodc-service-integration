from datetime import time
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlmodel import and_, col, desc, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.database.system_config import (
    ProjectConfigDBCreateDTO,
    ProjectConfigDBUpdateDTO,
    SystemConfigDBCreateDTO,
    SystemConfigDBUpdateDTO,
)
from src.domain.models.system_config import ConfigScope, ConfigType, ProjectConfigModel, SystemConfigModel
from src.domain.repositories.system_config_repository import ISystemConfigRepository
from src.infrastructure.entities.system_config import ProjectConfigEntity, SystemConfigEntity


class SQLAlchemySystemConfigRepository(ISystemConfigRepository):
    """Repository for system configuration"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_system_config_model(self, entity: SystemConfigEntity, project_configs: List[ProjectConfigEntity] = None) -> SystemConfigModel:
        """Convert entity to model"""
        # Determine the value based on type
        value: Union[int, float, str, bool, time, None] = None

        if entity.type == ConfigType.INT and entity.int_value is not None:
            value = entity.int_value
        elif entity.type == ConfigType.FLOAT and entity.float_value is not None:
            value = entity.float_value
        elif entity.type == ConfigType.STRING and entity.string_value is not None:
            value = entity.string_value
        elif entity.type == ConfigType.BOOL and entity.bool_value is not None:
            value = entity.bool_value
        elif entity.type == ConfigType.TIME and entity.time_value is not None:
            value = entity.time_value

        # Convert project configs if provided
        project_config_models = []
        if project_configs:
            for project_config in project_configs:
                project_config_models.append(self._to_project_config_model(project_config))

        return SystemConfigModel(
            id=entity.id,
            key=entity.key,
            scope=entity.scope,
            type=entity.type,
            value=value,
            description=entity.description,
            created_at=entity.created_at.isoformat() if entity.created_at else None,
            updated_at=entity.updated_at.isoformat() if entity.updated_at else None,
            project_configs=project_config_models
        )

    def _to_project_config_model(self, entity: ProjectConfigEntity) -> ProjectConfigModel:
        """Convert project config entity to model"""
        # Determine the value based on parent config type
        value: Union[int, float, str, bool, time, None] = None
        system_config_type = None

        if entity.system_config:
            system_config_type = entity.system_config.type

            if system_config_type == ConfigType.INT and entity.int_value is not None:
                value = entity.int_value
            elif system_config_type == ConfigType.FLOAT and entity.float_value is not None:
                value = entity.float_value
            elif system_config_type == ConfigType.STRING and entity.string_value is not None:
                value = entity.string_value
            elif system_config_type == ConfigType.BOOL and entity.bool_value is not None:
                value = entity.bool_value
            elif system_config_type == ConfigType.TIME and entity.time_value is not None:
                value = entity.time_value

        return ProjectConfigModel(
            id=entity.id,
            project_key=entity.project_key,
            system_config_id=entity.system_config_id,
            value=value,
            created_at=entity.created_at.isoformat() if entity.created_at else None,
            updated_at=entity.updated_at.isoformat() if entity.updated_at else None
        )

    def _prepare_system_config_entity(self, dto: Union[SystemConfigDBCreateDTO, SystemConfigDBUpdateDTO],
                                      is_update: bool = False) -> Dict[str, Any]:
        """Prepare entity values from DTO"""
        entity_data = {}

        # Only set key and scope for creates or if provided in updates
        if not is_update or dto.key is not None:
            entity_data["key"] = dto.key

        if not is_update or dto.scope is not None:
            entity_data["scope"] = dto.scope

        if not is_update or dto.type is not None:
            entity_data["type"] = dto.type

        if not is_update or dto.description is not None:
            entity_data["description"] = dto.description

        # Reset all value fields
        if not is_update or dto.type is not None:
            entity_data["int_value"] = None
            entity_data["float_value"] = None
            entity_data["string_value"] = None
            entity_data["bool_value"] = None
            entity_data["time_value"] = None

        # Set the appropriate value field
        config_type = dto.type if not is_update else (dto.type or ConfigType.STRING)

        if config_type == ConfigType.INT:
            entity_data["int_value"] = dto.int_value
        elif config_type == ConfigType.FLOAT:
            entity_data["float_value"] = dto.float_value
        elif config_type == ConfigType.STRING:
            entity_data["string_value"] = dto.string_value
        elif config_type == ConfigType.BOOL:
            entity_data["bool_value"] = dto.bool_value
        elif config_type == ConfigType.TIME:
            entity_data["time_value"] = dto.time_value

        return entity_data

    def _prepare_project_config_entity(self, dto: Union[ProjectConfigDBCreateDTO, ProjectConfigDBUpdateDTO],
                                       config_type: ConfigType,
                                       is_update: bool = False) -> Dict[str, Any]:
        """Prepare project config entity values from DTO"""
        entity_data = {}

        # Only set project_key and system_config_id for creates or if provided in updates
        if not is_update or dto.project_key is not None:
            entity_data["project_key"] = dto.project_key

        if not is_update or dto.system_config_id is not None:
            entity_data["system_config_id"] = dto.system_config_id

        # Reset all value fields
        entity_data["int_value"] = None
        entity_data["float_value"] = None
        entity_data["string_value"] = None
        entity_data["bool_value"] = None
        entity_data["time_value"] = None

        # Set the appropriate value field based on config type
        if config_type == ConfigType.INT:
            entity_data["int_value"] = dto.int_value
        elif config_type == ConfigType.FLOAT:
            entity_data["float_value"] = dto.float_value
        elif config_type == ConfigType.STRING:
            entity_data["string_value"] = dto.string_value
        elif config_type == ConfigType.BOOL:
            entity_data["bool_value"] = dto.bool_value
        elif config_type == ConfigType.TIME:
            entity_data["time_value"] = dto.time_value

        return entity_data

    async def get(self, id: int) -> Optional[SystemConfigModel]:
        """Get configuration by ID"""
        entity = await self.session.get(SystemConfigEntity, id)
        if not entity:
            return None

        # Get associated project configs
        result = await self.session.exec(
            select(ProjectConfigEntity).where(
                col(ProjectConfigEntity.system_config_id) == id
            )
        )
        project_configs = result.all()

        return self._to_system_config_model(entity, project_configs)

    async def get_by_key(self, key: str, scope: ConfigScope = ConfigScope.GENERAL) -> Optional[SystemConfigModel]:
        """Get configuration by key and scope"""
        query = select(SystemConfigEntity).where(
            and_(
                col(SystemConfigEntity.key) == key,
                col(SystemConfigEntity.scope) == scope
            )
        )
        result = await self.session.exec(query)
        entity = result.first()

        if not entity:
            return None

        # Get associated project configs
        result = await self.session.exec(
            select(ProjectConfigEntity).where(
                col(ProjectConfigEntity.system_config_id) == entity.id
            )
        )
        project_configs = result.all()

        return self._to_system_config_model(entity, project_configs)

    async def get_project_config(self, system_config_id: int, project_key: str) -> Optional[ProjectConfigModel]:
        """Get project-specific configuration"""
        query = select(ProjectConfigEntity).where(
            and_(
                col(ProjectConfigEntity.system_config_id) == system_config_id,
                col(ProjectConfigEntity.project_key) == project_key
            )
        )
        result = await self.session.exec(query)
        entity = result.first()

        if not entity:
            return None

        return self._to_project_config_model(entity)

    async def get_project_config_by_id(self, id: int) -> Optional[ProjectConfigModel]:
        """Get project-specific configuration by ID"""
        entity = await self.session.get(ProjectConfigEntity, id)
        if not entity:
            return None

        # Load the associated system config
        system_config = await self.session.get(SystemConfigEntity, entity.system_config_id)
        entity.system_config = system_config

        return self._to_project_config_model(entity)

    async def get_by_key_for_project(self, key: str, project_key: str) -> Optional[SystemConfigModel]:
        """Get config for project with fallback to general scope"""
        # First try to get the config at project scope
        project_scope_config = await self.get_by_key(key, ConfigScope.PROJECT)

        if not project_scope_config:
            # If not found, try general scope
            return await self.get_by_key(key, ConfigScope.GENERAL)

        # If found, check if we have a project-specific value
        result = await self.session.exec(
            select(ProjectConfigEntity).where(
                and_(
                    col(ProjectConfigEntity.system_config_id) == project_scope_config.id,
                    col(ProjectConfigEntity.project_key) == project_key
                )
            )
        )
        project_config = result.first()

        if not project_config:
            # Return the config with the default value
            return project_scope_config

        # Create a copy of the config with the project-specific value
        project_value = None
        if project_scope_config.type == ConfigType.INT and project_config.int_value is not None:
            project_value = project_config.int_value
        elif project_scope_config.type == ConfigType.FLOAT and project_config.float_value is not None:
            project_value = project_config.float_value
        elif project_scope_config.type == ConfigType.STRING and project_config.string_value is not None:
            project_value = project_config.string_value
        elif project_scope_config.type == ConfigType.BOOL and project_config.bool_value is not None:
            project_value = project_config.bool_value
        elif project_scope_config.type == ConfigType.TIME and project_config.time_value is not None:
            project_value = project_config.time_value

        # If we found a project-specific value, use it
        if project_value is not None:
            project_scope_config.value = project_value

        return project_scope_config

    async def list(self, scope: Optional[ConfigScope] = None,
                   limit: int = 100, offset: int = 0,
                   search: Optional[str] = None,
                   sort_by: Optional[str] = None,
                   sort_order: Optional[str] = None) -> Tuple[List[SystemConfigModel], int]:
        """List configurations with pagination and sorting"""
        try:
            # Build basic query
            query = select(SystemConfigEntity)
            count_query = select(col(SystemConfigEntity.id))

            # Apply filters if provided
            filters = []
            if scope:
                filters.append(col(SystemConfigEntity.scope) == scope)

            # Apply search filter if provided
            if search:
                search_term = f"%{search}%"
                filters.append(
                    or_(
                        col(SystemConfigEntity.key).ilike(search_term),
                        col(SystemConfigEntity.description).ilike(search_term)
                    )
                )

            # Apply all filters
            if filters:
                filter_clause = and_(*filters)
                query = query.where(filter_clause)
                count_query = count_query.where(filter_clause)

            # Get total count
            count_result = await self.session.exec(count_query)
            total_count = len(list(count_result))

            # Apply sorting
            valid_sort_fields = {
                "id": SystemConfigEntity.id,
                "key": SystemConfigEntity.key,
                "scope": SystemConfigEntity.scope,
                "type": SystemConfigEntity.type,
                "description": SystemConfigEntity.description,
                "created_at": SystemConfigEntity.created_at,
                "updated_at": SystemConfigEntity.updated_at
            }

            if sort_by and sort_by in valid_sort_fields:
                sort_column = valid_sort_fields[sort_by]
                if sort_order and sort_order.lower() == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(sort_column)
            else:
                # Default sorting by updated_at desc
                query = query.order_by(desc(SystemConfigEntity.updated_at))

            # Apply pagination
            query = query.offset(offset).limit(limit)

            # Execute query
            result = await self.session.exec(query)
            entities = result.all()

            # Convert to domain models
            models = []
            for entity in entities:
                # Get associated project configs for each entity
                project_config_result = await self.session.exec(
                    select(ProjectConfigEntity).where(
                        col(ProjectConfigEntity.system_config_id) == entity.id
                    )
                )
                project_configs = project_config_result.all()

                models.append(self._to_system_config_model(entity, project_configs))

            return models, total_count
        except Exception as e:
            log.error(f"Error listing configurations: {str(e)}")
            raise

    async def list_for_project(self, project_key: str,
                               limit: int = 100, offset: int = 0) -> Tuple[List[SystemConfigModel], int]:
        """List configurations for a specific project"""
        # First get project-scope configs
        project_configs, project_count = await self.list(
            scope=ConfigScope.PROJECT,
            limit=limit,
            offset=offset
        )

        # Then get general configs
        general_configs, general_count = await self.list(
            scope=ConfigScope.GENERAL
        )

        # Now for each config, check if there are project-specific values
        result_configs = []

        # Process project-scoped configs first
        for config in project_configs:
            # Get the project-specific value if it exists
            project_config = await self.get_project_config(config.id, project_key)

            if project_config:
                # Clone the config and set the project-specific value
                config.value = project_config.value

            result_configs.append(config)

        # Now add general configs
        for config in general_configs:
            result_configs.append(config)

        return result_configs, len(result_configs)

    async def create(self, dto: SystemConfigDBCreateDTO) -> SystemConfigModel:
        """Create a new configuration"""
        try:
            # Prepare entity data
            entity_data = self._prepare_system_config_entity(dto)

            # Create entity
            entity = SystemConfigEntity(**entity_data)
            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)

            return self._to_system_config_model(entity)
        except Exception as e:
            log.error(f"Error creating system config: {str(e)}")
            await self.session.rollback()
            raise

    async def update(self, id: int, dto: SystemConfigDBUpdateDTO) -> Optional[SystemConfigModel]:
        """Update an existing configuration"""
        try:
            entity = await self.session.get(SystemConfigEntity, id)
            if not entity:
                return None

            # Prepare update data
            update_data = self._prepare_system_config_entity(dto, is_update=True)

            # Update entity fields
            for key, value in update_data.items():
                setattr(entity, key, value)

            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)

            # Get associated project configs
            result = await self.session.exec(
                select(ProjectConfigEntity).where(
                    col(ProjectConfigEntity.system_config_id) == id
                )
            )
            project_configs = result.all()

            return self._to_system_config_model(entity, project_configs)
        except Exception as e:
            log.error(f"Error updating system config: {str(e)}")
            await self.session.rollback()
            raise

    async def create_project_config(self, dto: ProjectConfigDBCreateDTO) -> ProjectConfigModel:
        """Create a project-specific configuration"""
        try:
            # Get the system config to determine type
            system_config = await self.session.get(SystemConfigEntity, dto.system_config_id)
            if not system_config:
                raise ValueError(f"System config with ID {dto.system_config_id} not found")

            # Prepare entity data
            entity_data = self._prepare_project_config_entity(dto, system_config.type)

            # Create entity
            entity = ProjectConfigEntity(**entity_data)
            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)

            # Ensure the entity has the system_config loaded
            entity.system_config = system_config

            return self._to_project_config_model(entity)
        except Exception as e:
            log.error(f"Error creating project config: {str(e)}")
            await self.session.rollback()
            raise

    async def update_project_config(self, id: int, dto: ProjectConfigDBUpdateDTO) -> Optional[ProjectConfigModel]:
        """Update a project-specific configuration"""
        try:
            entity = await self.session.get(ProjectConfigEntity, id)
            if not entity:
                return None

            log.info(f"entity: {entity}")
            # Get the system config to determine type
            system_config_id = dto.system_config_id or entity.system_config_id
            system_config = await self.session.get(SystemConfigEntity, system_config_id)
            if not system_config:
                raise ValueError(f"System config with ID {system_config_id} not found")

            # Prepare update data
            update_data = self._prepare_project_config_entity(dto, system_config.type, is_update=True)

            # Update entity fields
            for key, value in update_data.items():
                setattr(entity, key, value)

            self.session.add(entity)
            await self.session.commit()
            await self.session.refresh(entity)

            # Ensure the entity has the system_config loaded
            entity.system_config = system_config

            return self._to_project_config_model(entity)
        except Exception as e:
            log.error(f"Error updating project config: {str(e)}")
            await self.session.rollback()
            raise

    async def delete(self, id: int) -> bool:
        """Delete a configuration"""
        try:
            entity = await self.session.get(SystemConfigEntity, id)
            if not entity:
                return False

            # First delete associated project configs
            result = await self.session.exec(
                select(ProjectConfigEntity).where(
                    col(ProjectConfigEntity.system_config_id) == id
                )
            )
            project_configs = result.all()

            for project_config in project_configs:
                await self.session.delete(project_config)

            # Then delete the system config
            await self.session.delete(entity)
            await self.session.commit()

            return True
        except Exception as e:
            log.error(f"Error deleting system config: {str(e)}")
            await self.session.rollback()
            raise

    async def delete_project_config(self, id: int) -> bool:
        """Delete a project-specific configuration"""
        try:
            entity = await self.session.get(ProjectConfigEntity, id)
            if not entity:
                return False

            await self.session.delete(entity)
            await self.session.commit()

            return True
        except Exception as e:
            log.error(f"Error deleting project config: {str(e)}")
            await self.session.rollback()
            raise

    async def upsert(self, dto: SystemConfigDBCreateDTO) -> SystemConfigModel:
        """Create or update a configuration based on key and scope"""
        try:
            # Check if config exists
            result = await self.session.exec(
                select(SystemConfigEntity).where(
                    and_(
                        col(SystemConfigEntity.key) == dto.key,
                        col(SystemConfigEntity.scope) == dto.scope
                    )
                )
            )
            entity = result.first()

            if entity:
                # Update existing
                update_dto = SystemConfigDBUpdateDTO(**dto.dict())
                return await self.update(entity.id, update_dto)
            else:
                # Create new
                return await self.create(dto)
        except Exception as e:
            log.error(f"Error upserting system config: {str(e)}")
            raise

    async def upsert_project_config(self, dto: ProjectConfigDBCreateDTO) -> ProjectConfigModel:
        """Create or update a project-specific configuration"""
        try:
            # Check if config exists
            result = await self.session.exec(
                select(ProjectConfigEntity).where(
                    and_(
                        col(ProjectConfigEntity.system_config_id) == dto.system_config_id,
                        col(ProjectConfigEntity.project_key) == dto.project_key
                    )
                )
            )
            entity = result.first()

            if entity:
                # Update existing
                update_dto = ProjectConfigDBUpdateDTO(**dto.dict())
                return await self.update_project_config(entity.id, update_dto)
            else:
                # Create new
                return await self.create_project_config(dto)
        except Exception as e:
            log.error(f"Error upserting project config: {str(e)}")
            raise
