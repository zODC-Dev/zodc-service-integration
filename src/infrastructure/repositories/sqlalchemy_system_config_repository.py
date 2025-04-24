from datetime import time
from typing import List, Optional, Union

from sqlmodel import and_, col, desc, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.logger import log
from src.domain.models.system_config import ConfigScope, ConfigType, SystemConfigModel
from src.domain.repositories.system_config_repository import ISystemConfigRepository
from src.infrastructure.entities.system_config import SystemConfigEntity


class SQLAlchemySystemConfigRepository(ISystemConfigRepository):
    """Repository for system configuration"""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_model(self, entity: SystemConfigEntity) -> SystemConfigModel:
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

        return SystemConfigModel(
            id=entity.id,
            key=entity.key,
            scope=entity.scope,
            project_key=entity.project_key,
            type=entity.type,
            value=value,
            description=entity.description,
            created_at=entity.created_at.isoformat() if entity.created_at else None,
            updated_at=entity.updated_at.isoformat() if entity.updated_at else None
        )

    def _to_entity(self, model: SystemConfigModel) -> SystemConfigEntity:
        """Convert model to entity"""
        entity = SystemConfigEntity(
            key=model.key,
            scope=model.scope,
            project_key=model.project_key,
            type=model.type,
            description=model.description,
        )

        if model.id:
            entity.id = model.id

        # Set the value based on type
        if model.type == ConfigType.INT and isinstance(model.value, int):
            entity.int_value = model.value
        elif model.type == ConfigType.FLOAT and isinstance(model.value, float):
            entity.float_value = model.value
        elif model.type == ConfigType.STRING and isinstance(model.value, str):
            entity.string_value = model.value
        elif model.type == ConfigType.BOOL and isinstance(model.value, bool):
            entity.bool_value = model.value
        elif model.type == ConfigType.TIME and isinstance(model.value, time):
            entity.time_value = model.value

        return entity

    async def get(self, id: int) -> Optional[SystemConfigModel]:
        """Get configuration by ID"""
        entity = await self.session.get(SystemConfigEntity, id)
        if not entity:
            return None
        return self._to_model(entity)

    async def get_by_key(self, key: str, scope: ConfigScope = ConfigScope.GENERAL,
                         project_key: Optional[str] = None) -> Optional[SystemConfigModel]:
        """Get configuration by key, scope and project_key"""
        query = select(SystemConfigEntity).where(
            and_(
                col(SystemConfigEntity.key) == key,
                col(SystemConfigEntity.scope) == scope,
                col(SystemConfigEntity.project_key) == project_key
            )
        )
        result = await self.session.exec(query)
        entity = result.first()
        if not entity:
            return None
        return self._to_model(entity)

    async def get_by_key_with_fallback(self, key: str, project_key: str) -> Optional[SystemConfigModel]:
        """Get configuration by key and project_key.

        If project config doesn't exist, fall back to global config.
        """
        # First try project-specific config
        project_config = await self.get_by_key(key, ConfigScope.PROJECT, project_key)
        if project_config:
            return project_config

        # Fall back to global config
        return await self.get_by_key(key, ConfigScope.GENERAL)

    async def list(self, scope: Optional[ConfigScope] = None,
                   project_key: Optional[str] = None,
                   limit: int = 100, offset: int = 0,
                   search: Optional[str] = None,
                   sort_by: Optional[str] = None,
                   sort_order: Optional[str] = None) -> tuple[List[SystemConfigModel], int]:
        """List configurations with pagination, search, and sorting"""
        try:
            # Build basic query
            query = select(SystemConfigEntity)
            count_query = select(col(SystemConfigEntity.id))

            # Apply filters if provided
            filters = []
            if scope:
                filters.append(col(SystemConfigEntity.scope) == scope)

            if project_key:
                filters.append(col(SystemConfigEntity.project_key) == project_key)

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
                "project_key": SystemConfigEntity.project_key,
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
                # Default sorting
                query = query.order_by(desc(col(SystemConfigEntity.updated_at)))

            # Apply pagination
            query = query.offset(offset).limit(limit)

            # Execute query
            result = await self.session.exec(query)
            entities = result.all()

            # Convert to domain models
            return [self._to_model(entity) for entity in entities], total_count
        except Exception as e:
            log.error(f"Error listing configurations: {str(e)}")
            raise

    async def create(self, model: SystemConfigModel) -> SystemConfigModel:
        """Create a new configuration"""
        entity = self._to_entity(model)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return self._to_model(entity)

    async def update(self, model: SystemConfigModel) -> Optional[SystemConfigModel]:
        """Update an existing configuration"""
        if not model.id:
            return None

        entity = await self.session.get(SystemConfigEntity, model.id)
        if not entity:
            return None

        # Clear all value fields first
        entity.int_value = None
        entity.float_value = None
        entity.string_value = None
        entity.bool_value = None
        entity.time_value = None

        # Update all fields
        entity.key = model.key
        entity.scope = model.scope
        entity.project_key = model.project_key
        entity.type = model.type
        entity.description = model.description

        # Set the value based on type
        if model.type == ConfigType.INT and isinstance(model.value, int):
            entity.int_value = model.value
        elif model.type == ConfigType.FLOAT and isinstance(model.value, float):
            entity.float_value = model.value
        elif model.type == ConfigType.STRING and isinstance(model.value, str):
            entity.string_value = model.value
        elif model.type == ConfigType.BOOL and isinstance(model.value, bool):
            entity.bool_value = model.value
        elif model.type == ConfigType.TIME and isinstance(model.value, time):
            entity.time_value = model.value

        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return self._to_model(entity)

    async def delete(self, id: int) -> bool:
        """Delete a configuration"""
        entity = await self.session.get(SystemConfigEntity, id)
        if not entity:
            return False
        await self.session.delete(entity)
        await self.session.commit()
        return True

    async def upsert(self, model: SystemConfigModel) -> SystemConfigModel:
        """Create or update a configuration based on key, scope and project_key"""
        # Try to find existing config
        query = select(SystemConfigEntity).where(
            and_(
                col(SystemConfigEntity.key) == model.key,
                col(SystemConfigEntity.scope) == model.scope,
                col(SystemConfigEntity.project_key) == model.project_key
            )
        )
        result = await self.session.exec(query)
        existing = result.first()

        if existing:
            # Update existing
            model.id = existing.id
            return await self.update(model)
        else:
            # Create new
            return await self.create(model)

    async def bulk_upsert(self, configs: List[SystemConfigModel]) -> List[SystemConfigModel]:
        """Bulk create or update configurations"""
        results = []
        for config in configs:
            results.append(await self.upsert(config))
        return results
