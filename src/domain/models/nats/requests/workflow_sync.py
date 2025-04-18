from typing import List, Optional

from pydantic import BaseModel


class WorkflowSyncIssue(BaseModel):
    node_id: str
    type: str  # "Story", "Task", "Bug", etc.
    title: str
    assignee_id: Optional[int] = None  # System user id
    jira_key: Optional[str] = None
    estimate_point: Optional[float] = None
    action: str  # "create" hoặc "update"


class WorkflowSyncConnection(BaseModel):
    from_issue_key: str  # Có thể là jira_key hoặc node_id
    to_issue_key: str    # Có thể là jira_key hoặc node_id
    type: str            # "relates to" hoặc "contains"


class WorkflowSyncRequest(BaseModel):
    transaction_id: str
    project_key: str
    sprint_id: Optional[int] = None  # System sprint id, can be None if not specified
    issues: List[WorkflowSyncIssue]
    connections: List[WorkflowSyncConnection]
