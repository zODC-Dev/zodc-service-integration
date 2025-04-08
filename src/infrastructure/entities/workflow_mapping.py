from typing import Optional

from sqlmodel import Field

from src.infrastructure.entities.base import BaseEntityWithTimestamps


class WorkflowMappingEntity(BaseEntityWithTimestamps, table=True):
    __tablename__ = "workflow_mappings"

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True, unique=True)  # External workflow ID
    transaction_id: str = Field(index=True)
    project_key: str = Field(foreign_key="jira_projects.key", index=True)
    sprint_id: int = Field(index=True)  # System sprint ID
    name: Optional[str] = None
    description: Optional[str] = None
    status: str = Field(default="active")  # active, completed, archived
    # created_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
    # updated_at: datetime = Field(sa_column=Column(DateTime(timezone=True)))
