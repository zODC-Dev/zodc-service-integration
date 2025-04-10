from typing import List, Optional

from pydantic import BaseModel


class WorkflowSyncIssue(BaseModel):
    node_id: str
    type: str  # "Story", "TASK", "BUG", etc.
    title: str
    assignee_id: Optional[int] = None
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
    sprint_id: int  # System sprint id
    issues: List[WorkflowSyncIssue]
    connections: List[WorkflowSyncConnection]
