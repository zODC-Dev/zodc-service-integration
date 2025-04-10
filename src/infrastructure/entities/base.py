from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Column, DateTime, Field, SQLModel


class BaseEntity(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True,
                              index=True, sa_column_kwargs={"autoincrement": True})


class BaseEntityWithTimestamps(BaseEntity):
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )


class BaseEntityWithTimestampsAndUpdatedAt(BaseEntityWithTimestamps):
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))


class BaseEntityWithTimestampsAndSoftDelete(BaseEntityWithTimestampsAndUpdatedAt):
    deleted_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True)))
