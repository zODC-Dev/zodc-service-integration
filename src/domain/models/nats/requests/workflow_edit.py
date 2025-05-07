from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class WorkflowEditIssue(BaseModel):
    node_id: str
    type: str  # "Story", "TASK", "BUG", etc.
    title: str
    assignee_id: Optional[int] = None
    jira_key: Optional[str] = None
    estimate_point: Optional[float] = None
    action: str  # "create" hoặc "update"
    last_synced_at: Optional[datetime] = None


class WorkflowEditConnection(BaseModel):
    from_issue_key: str  # node_id
    to_issue_key: str    # node_id
    type: str            # "relates to" hoặc "contains"


class NodeJiraMapping(BaseModel):
    node_id: str
    jira_key: str


class WorkflowEditRequest(BaseModel):
    transaction_id: str
    project_key: str
    sprint_id: Optional[int] = None  # system sprint id, can be None if not specified
    issues: List[WorkflowEditIssue]  # Các issue mới/cập nhật
    connections: List[WorkflowEditConnection]  # Các connections mới
    connections_to_remove: List[WorkflowEditConnection]  # Các connections cần xóa
    node_mappings: List[NodeJiraMapping] = []  # Mappings giữa node IDs và Jira keys
