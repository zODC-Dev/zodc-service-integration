from typing import Optional

from pydantic import BaseModel


class JiraBoardModel(BaseModel):
    """Domain model for Jira Board"""
    id: int
    name: str
    type: str
    project_id: Optional[int] = None
    project_key: Optional[str] = None

    class Config:
        from_attributes = True
