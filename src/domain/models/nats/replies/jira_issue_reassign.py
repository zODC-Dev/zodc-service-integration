from datetime import datetime
from pydantic import BaseModel, Field


class JiraIssueReassignNATSReplyDTO(BaseModel):
    success: bool = Field(..., description="Whether reassignment was successful")
    jira_key: str = Field(..., description="Jira issue key")
    node_id: int = Field(..., description="Node ID in system")
    old_user_id: int = Field(..., description="Old user ID in system")
    new_user_id: int = Field(..., description="New user ID in system")
    timestamp: datetime = Field(default_factory=datetime.now)
    error_message: str = Field(None, description="Error message if operation failed")
