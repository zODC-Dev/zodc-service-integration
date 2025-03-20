from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from .base import JiraAPIResponseBase
from .common import JiraAPIProjectBaseResponse, JiraAPIUserResponse


class JiraAPIProjectResponse(JiraAPIProjectBaseResponse):
    """Full project response with all fields"""
    pass


class JiraAPIProjectIssueResponse(JiraAPIResponseBase):
    id: str
    key: str
    fields: Dict[str, Any]


class JiraAPIProjectSprintResponse(BaseModel):
    id: int
    name: str
    state: str
    start_date: Optional[datetime] = Field(alias="startDate")
    end_date: Optional[datetime] = Field(alias="endDate")
    goal: Optional[str]

    class Config:
        populate_by_name = True


class JiraAPIProjectUserResponse(JiraAPIUserResponse):
    """Project-specific user response"""
    pass
