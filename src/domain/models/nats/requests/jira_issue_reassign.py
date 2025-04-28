from pydantic import BaseModel, Field


class JiraIssueReassignNATSRequestDTO(BaseModel):
    jira_key: str = Field(..., description="Jira issue key")
    node_id: str = Field(..., description="Node ID in system")
    old_user_id: int = Field(..., description="Old user ID in system")
    new_user_id: int = Field(..., description="New user ID in system")
