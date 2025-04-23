from typing import List, Optional

from pydantic import BaseModel


class WorkflowSyncReplyIssue(BaseModel):
    node_id: str
    jira_key: str
    jira_link_url: Optional[str] = None


class WorkflowSyncReply(BaseModel):
    issues: List[WorkflowSyncReplyIssue]
