from typing import List, Optional

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


class SyncedJiraUserDTO(BaseModel):
    """DTO for synced Jira user information in the reply"""
    id: Optional[int] = None
    jira_account_id: str
    name: str
    email: str = ""
    is_active: bool = True
    avatar_url: Optional[str] = None


class JiraProjectSyncNATSReplyDTO(BaseModel):
    success: bool
    project_key: str
    error_message: Optional[str] = None
    sync_summary: JiraProjectSyncSummaryDTO
    synced_users: List[SyncedJiraUserDTO] = []
