from typing import List

from pydantic import BaseModel


class WorkflowSyncReplyIssue(BaseModel):
    node_id: str
    jira_key: str


class WorkflowSyncReply(BaseModel):
    issues: List[WorkflowSyncReplyIssue]
