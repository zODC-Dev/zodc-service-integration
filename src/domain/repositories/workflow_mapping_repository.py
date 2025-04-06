from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.models.workflow_mapping import WorkflowMappingModel


class IWorkflowMappingRepository(ABC):
    """Interface for workflow mapping repository"""

    @abstractmethod
    async def create(self, workflow_mapping: WorkflowMappingModel) -> WorkflowMappingModel:
        """Create a new workflow mapping"""
        pass

    @abstractmethod
    async def get_by_workflow_id(self, workflow_id: str) -> Optional[WorkflowMappingModel]:
        """Get workflow mapping by workflow ID"""
        pass

    @abstractmethod
    async def get_by_transaction_id(self, transaction_id: str) -> Optional[WorkflowMappingModel]:
        """Get workflow mapping by transaction ID"""
        pass

    @abstractmethod
    async def get_by_sprint(self, sprint_id: int) -> List[WorkflowMappingModel]:
        """Get workflow mappings for a sprint"""
        pass

    @abstractmethod
    async def get_by_project(self, project_key: str) -> List[WorkflowMappingModel]:
        """Get workflow mappings for a project"""
        pass

    @abstractmethod
    async def update_status(self, workflow_id: str, status: str) -> Optional[WorkflowMappingModel]:
        """Update workflow mapping status"""
        pass
