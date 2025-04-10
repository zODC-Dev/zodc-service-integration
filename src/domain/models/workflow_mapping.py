from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class WorkflowMappingModel(BaseModel):
    """Domain model for workflow mapping"""
    id: Optional[int] = None
    workflow_id: str
    transaction_id: str
    project_key: str
    sprint_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
