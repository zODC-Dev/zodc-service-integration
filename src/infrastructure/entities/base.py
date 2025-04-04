from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class BaseEntity(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True,
                              index=True, sa_column_kwargs={"autoincrement": True})


class BaseEntityWithTimestamps(BaseEntity):
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)


class BaseEntityWithTimestampsAndSoftDelete(BaseEntityWithTimestamps):
    deleted_at: Optional[datetime] = Field(default=None)
