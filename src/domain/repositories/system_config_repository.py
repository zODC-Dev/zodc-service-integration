from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.system_config import ConfigScope, SystemConfigModel


class ISystemConfigRepository(ABC):
    """Repository interface for system configuration"""

    @abstractmethod
    async def get(self, id: int) -> Optional[SystemConfigModel]:
        """Get configuration by ID"""
        pass

    @abstractmethod
    async def get_by_key(self, key: str, scope: ConfigScope = ConfigScope.GLOBAL,
                         project_key: Optional[str] = None) -> Optional[SystemConfigModel]:
        """Get configuration by key, scope and project_key"""
        pass

    @abstractmethod
    async def get_by_key_with_fallback(self, key: str, project_key: str) -> Optional[SystemConfigModel]:
        """Get configuration by key and project_key.

        If project config doesn't exist, fall back to global config.
        """
        pass

    @abstractmethod
    async def list(self, scope: Optional[ConfigScope] = None,
                   project_key: Optional[str] = None,
                   limit: int = 100, offset: int = 0) -> List[SystemConfigModel]:
        """List configurations with pagination, optionally filtered by scope and project_key"""
        pass

    @abstractmethod
    async def create(self, model: SystemConfigModel) -> SystemConfigModel:
        """Create a new configuration"""
        pass

    @abstractmethod
    async def update(self, model: SystemConfigModel) -> Optional[SystemConfigModel]:
        """Update an existing configuration"""
        pass

    @abstractmethod
    async def delete(self, id: int) -> bool:
        """Delete a configuration"""
        pass

    @abstractmethod
    async def upsert(self, model: SystemConfigModel) -> SystemConfigModel:
        """Create or update a configuration based on key, scope and project_key"""
        pass

    @abstractmethod
    async def bulk_upsert(self, configs: List[SystemConfigModel]) -> List[SystemConfigModel]:
        """Bulk create or update configurations"""
        pass
