from typing import Optional

from pydantic import BaseModel


class JiraProjectSyncSummaryDTO(BaseModel):
    total_issues: int = 0
    synced_issues: int = 0
    total_sprints: int = 0
    synced_sprints: int = 0
    total_users: int = 0
    synced_users: int = 0
    started_at: str
    completed_at: Optional[str] = None


class JiraProjectSyncNATSReplyDTO(BaseModel):
    success: bool
    project_key: str
    error_message: Optional[str] = None
    sync_summary: JiraProjectSyncSummaryDTO
