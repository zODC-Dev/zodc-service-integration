
from pydantic import BaseModel


class JiraSprintStartRequestDTO(BaseModel):
    """DTO for starting a sprint"""
    sprint_id: int


class JiraSprintEndRequestDTO(BaseModel):
    """DTO for ending a sprint"""
    sprint_id: int
