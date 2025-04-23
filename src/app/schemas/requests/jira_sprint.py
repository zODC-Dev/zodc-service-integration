from datetime import datetime
from typing import Optional

from pydantic import Field

from src.app.schemas.requests.base import BaseRequest


class SprintStartRequest(BaseRequest):
    """Request model for starting a sprint"""
    start_date: Optional[datetime] = Field(
        None,
        description="Start date of the sprint. If not provided, current date will be used."
    )
    end_date: Optional[datetime] = Field(
        None,
        description="End date of the sprint. If not provided, start_date + 14 days will be used."
    )
    goal: Optional[str] = Field(
        None,
        description="Goal of the sprint."
    )
