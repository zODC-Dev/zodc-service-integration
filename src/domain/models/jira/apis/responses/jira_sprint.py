from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JiraSprintAPIGetResponseDTO(BaseModel):
    """DTO for sprint response from Jira API"""
    id: int
    name: str
    state: str
    start_date: Optional[str] = Field(None, alias="startDate")
    end_date: Optional[str] = Field(None, alias="endDate")
    complete_date: Optional[str] = Field(None, alias="completeDate")
    created_date: Optional[str] = Field(None, alias="createdDate")
    board_id: Optional[int] = Field(None, alias="boardId")
    origin_board_id: Optional[int] = Field(None, alias="originBoardId")
    goal: Optional[str] = None

    class Config:
        extra = "allow"
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
