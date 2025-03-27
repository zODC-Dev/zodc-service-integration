from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.domain.constants.jira import JiraActionType, JiraIssueStatus, JiraIssueType


class JiraIssueSyncNATSRequestDTO(BaseModel):
    user_id: int
    project_key: str
    issue_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    type: Optional[JiraIssueType] = None
    status: Optional[JiraIssueStatus] = None
    assignee_id: Optional[int] = None  # Internal user id
    sprint_id: Optional[int] = None  # Jira sprint id (if not provided, issue will be created in backlog)
    estimate_point: Optional[float] = None
    actual_point: Optional[float] = None
    action_type: JiraActionType


class JiraIssueBatchSyncNATSRequestDTO(BaseModel):
    issues: List[JiraIssueSyncNATSRequestDTO]


class JiraIssueLinkDTO(BaseModel):
    """DTO for linking issues in Jira"""
    source_issue_id: str = Field(..., description="ID of the source issue")
    target_issue_id: str = Field(..., description="ID of the target issue")
    # Only use relationship "relates"


class JiraIssueBatchLinkNATSRequestDTO(BaseModel):
    """DTO for batch processing issue link via NATS"""
    user_id: int = Field(..., description="ID of the user performing the action")
    project_key: str = Field(..., description="Key of the project")

    # List of links to create
    links: List[JiraIssueLinkDTO] = Field(default_factory=list, description="List of links between issues")

    # Additional data (if needed)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
