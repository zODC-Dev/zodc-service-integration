from datetime import time
from typing import Optional

from sqlmodel import Column, Field, Time, UniqueConstraint

from src.infrastructure.entities.base import BaseEntityWithTimestampsAndUpdatedAt


class SystemConfigEntity(BaseEntityWithTimestampsAndUpdatedAt, table=True):
    """Entity for system configuration"""
    __tablename__ = "system_configs"

    key: str = Field(index=True)
    scope: str = Field(index=True)
    project_key: Optional[str] = Field(default=None, index=True)
    type: str = Field()

    # Different value types
    int_value: Optional[int] = Field(default=None)
    float_value: Optional[float] = Field(default=None)
    string_value: Optional[str] = Field(default=None)
    bool_value: Optional[bool] = Field(default=None)
    time_value: Optional[time] = Field(default=None, sa_column=Column(Time))

    description: Optional[str] = Field(default=None)

    # Define a unique constraint
    __table_args__ = (
        UniqueConstraint('key', 'scope', 'project_key', name='uq_system_configs_key_scope_project'),
    )
