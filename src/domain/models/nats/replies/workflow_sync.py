from typing import List, Optional

from pydantic import BaseModel


class WorkflowSyncReplyIssue(BaseModel):
    node_id: str
    jira_key: str
    jira_link_url: Optional[str] = None


class WorkflowSyncReply(BaseModel):
    success: bool
    error_message: Optional[str] = None
    issues: List[WorkflowSyncReplyIssue]
