from datetime import datetime
from typing import Optional

from pydantic import Field

from src.app.schemas.requests.base import BaseRequest


class SprintStartRequest(BaseRequest):
    """Request model for starting a sprint"""
    start_date: datetime
    end_date: datetime
    goal: Optional[str] = Field(None, description="Goal of the sprint.")
