from datetime import datetime, time, timezone
from typing import List, Optional

from sqlmodel import Column, DateTime, Field, Relationship, SQLModel, Time, UniqueConstraint


class SystemConfigEntity(SQLModel, table=True):
    """Entity for system configuration"""
    __tablename__ = "system_configs"

    id: Optional[int] = Field(default=None, primary_key=True)

    key: str = Field(index=True)
    scope: str = Field(index=True)
    type: str = Field()

    # Different value types
    int_value: Optional[int] = Field(default=None)
    float_value: Optional[float] = Field(default=None)
    string_value: Optional[str] = Field(default=None)
    bool_value: Optional[bool] = Field(default=None)
    time_value: Optional[time] = Field(default=None, sa_column=Column(Time))

    description: Optional[str] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Relationship with projects
    project_configs: List["ProjectConfigEntity"] = Relationship(back_populates="system_config")

    # Define a unique constraint
    __table_args__ = (
        UniqueConstraint('key', 'scope', name='uq_system_configs_key_scope'),
    )


class ProjectConfigEntity(SQLModel, table=True):
    """Entity for project-specific configurations"""
    __tablename__ = "project_configs"

    id: Optional[int] = Field(default=None, primary_key=True)

    project_key: str = Field(index=True)
    system_config_id: int = Field(foreign_key="system_configs.id", index=True)

    # Different value types
    int_value: Optional[int] = Field(default=None)
    float_value: Optional[float] = Field(default=None)
    string_value: Optional[str] = Field(default=None)
    bool_value: Optional[bool] = Field(default=None)
    time_value: Optional[time] = Field(default=None, sa_column=Column(Time))

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))

    # Relationship with system config
    system_config: "SystemConfigEntity" = Relationship(
        back_populates="project_configs",
        sa_relationship_kwargs={'lazy': 'selectin'}
    )

    # Define a unique constraint
    __table_args__ = (
        UniqueConstraint('project_key', 'system_config_id', name='uq_project_configs_project_system_config'),
    )
