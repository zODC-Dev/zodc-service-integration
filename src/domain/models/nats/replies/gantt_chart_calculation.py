from datetime import datetime
from typing import List, Optional, Any, Dict

from pydantic import BaseModel, Field


def datetime_encoder(obj: Any) -> Any:
    """Custom encoder for datetime objects"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class GanttChartJiraIssueResult(BaseModel):
    """Result model for a Jira issue in Gantt chart calculation"""
    node_id: str = Field(..., alias="node_id")
    planned_start_time: datetime = Field(..., alias="planned_start_time")
    planned_end_time: datetime = Field(..., alias="planned_end_time")


class GanttChartCalculationResponse(BaseModel):
    """Response model for Gantt chart calculation matching Go client expectations"""
    issues: List[GanttChartJiraIssueResult]

    def model_dump_json(self, **kwargs) -> str:
        """Override to handle datetime serialization"""
        return super().model_dump_json(encoder=datetime_encoder, **kwargs)
