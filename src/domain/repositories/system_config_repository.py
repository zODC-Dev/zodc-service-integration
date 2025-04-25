from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.database.system_config import (
    ProjectConfigDBCreateDTO,
    ProjectConfigDBUpdateDTO,
    SystemConfigDBCreateDTO,
    SystemConfigDBUpdateDTO,
)
from src.domain.models.system_config import ConfigScope, ProjectConfigModel, SystemConfigModel


class ISystemConfigRepository(ABC):
    """Repository interface for system configuration"""

    @abstractmethod
    async def get(self, id: int) -> Optional[SystemConfigModel]:
        """Get configuration by ID"""
        pass

    @abstractmethod
    async def get_by_key(self, key: str, scope: ConfigScope = ConfigScope.GENERAL) -> Optional[SystemConfigModel]:
        """Get configuration by key and scope"""
        pass

    @abstractmethod
    async def get_project_config(self, system_config_id: int, project_key: str) -> Optional[ProjectConfigModel]:
        """Get project-specific configuration by system config ID and project key"""
        pass

    @abstractmethod
    async def get_project_config_by_id(self, id: int) -> Optional[ProjectConfigModel]:
        """Get project-specific configuration by ID"""
        pass

    @abstractmethod
    async def get_by_key_for_project(self, key: str, project_key: str) -> Optional[SystemConfigModel]:
        """Get configuration by key for a specific project with fallback to general config"""
        pass

    @abstractmethod
    async def list(self, scope: Optional[ConfigScope] = None,
                   limit: int = 100, offset: int = 0,
                   search: Optional[str] = None,
                   sort_by: Optional[str] = None,
                   sort_order: Optional[str] = None) -> tuple[List[SystemConfigModel], int]:
        """List configurations with pagination, optionally filtered by scope.

        Args:
            scope: Filter by configuration scope
            limit: Maximum number of results to return
            offset: Offset for pagination
            search: Search term for filtering by key or description
            sort_by: Field to sort by (id, key, scope, type)
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple containing the list of configuration models and the total count
        """
        pass

    @abstractmethod
    async def list_for_project(self, project_key: str,
                               limit: int = 100, offset: int = 0) -> tuple[List[SystemConfigModel], int]:
        """List configurations for a specific project including general configs.

        Args:
            project_key: Project key
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            Tuple containing the list of configuration models and the total count
        """
        pass

    @abstractmethod
    async def create(self, dto: SystemConfigDBCreateDTO) -> SystemConfigModel:
        """Create a new configuration"""
        pass

    @abstractmethod
    async def update(self, id: int, dto: SystemConfigDBUpdateDTO) -> Optional[SystemConfigModel]:
        """Update an existing configuration"""
        pass

    @abstractmethod
    async def create_project_config(self, dto: ProjectConfigDBCreateDTO) -> ProjectConfigModel:
        """Create a project-specific configuration"""
        pass

    @abstractmethod
    async def update_project_config(self, id: int, dto: ProjectConfigDBUpdateDTO) -> Optional[ProjectConfigModel]:
        """Update a project-specific configuration"""
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete a configuration"""
        pass

    @abstractmethod
    async def delete_project_config(self, id: int) -> bool:
        """Delete a project-specific configuration"""
        pass

    @abstractmethod
    async def upsert(self, dto: SystemConfigDBCreateDTO) -> SystemConfigModel:
        """Create or update a configuration based on key and scope"""
        pass

    @abstractmethod
    async def upsert_project_config(self, dto: ProjectConfigDBCreateDTO) -> ProjectConfigModel:
        """Create or update a project-specific configuration"""
        pass
