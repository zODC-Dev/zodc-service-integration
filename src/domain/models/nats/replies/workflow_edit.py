from typing import List

from pydantic import BaseModel


class WorkflowEditReplyIssue(BaseModel):
    node_id: str
    jira_key: str


class WorkflowEditReply(BaseModel):
    issues: List[WorkflowEditReplyIssue]
    removed_connections: int  # Số connections đã xóa thành công
    added_connections: int    # Số connections đã thêm thành công
