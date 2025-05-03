from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel

from src.domain.models.jira.apis.responses.jira_user import JiraUserAPIGetResponseDTO


class JiraIssueCommentAPIGetResponseDTO(BaseModel):
    id: str
    author: JiraUserAPIGetResponseDTO
    body: Dict[str, Any]  # ADF formatted body
    rendered_body: Optional[str] = Field(default=None, alias="renderedBody")  # Rendered body with HTML format
    created: datetime

    class Config:
        populate_by_name = True
        alias_generator = to_camel
