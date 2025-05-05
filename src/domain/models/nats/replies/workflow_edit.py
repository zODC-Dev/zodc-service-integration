from typing import List, Optional

from pydantic import BaseModel, Field


class WorkflowEditReplyIssue(BaseModel):
    node_id: str
    jira_key: str
    jira_link_url: Optional[str] = None


class WorkflowEditReply(BaseModel):
    success: Optional[bool] = Field(default=True, description="Success")
    error_message: Optional[str] = Field(default=None, description="Error message")
    issues: List[WorkflowEditReplyIssue]
    removed_connections: int  # Số connections đã xóa thành công
    added_connections: int    # Số connections đã thêm thành công
