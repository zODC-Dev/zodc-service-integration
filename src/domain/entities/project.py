from typing import Optional

from pydantic import BaseModel

from .base import BaseEntity


class Project(BaseEntity):
    name: str
    key: str

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    key: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    key: Optional[str] = None
    description: Optional[str] = None
