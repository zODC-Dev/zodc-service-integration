from typing import List, Optional

from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel


class JiraIssueHistoryBulkFetchRequestDTO(BaseModel):
    issue_ids_or_keys: List[str] = Field(..., description="List of issue IDs or keys", alias="issueIdsOrKeys")
    field_ids: Optional[List[str]] = Field(None, description="List of field IDs", alias="fieldIds")

    class Config:
        populate_by_name = True
        alias_generator = to_camel
