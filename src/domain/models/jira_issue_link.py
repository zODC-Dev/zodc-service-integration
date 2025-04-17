from enum import Enum
from typing import Optional
from pydantic import BaseModel


class JiraIssueLinkDirection(str, Enum):
    """Direction of issue link relative to the source issue"""
    INWARD = "inward"
    OUTWARD = "outward"


class IssueLinkType(BaseModel):
    """Type of issue link"""
    id: str
    name: str
    inward_description: str  # e.g. "relates to"
    outward_description: str  # e.g. "relates to"


class LinkedIssue(BaseModel):
    """Issue linked to another issue"""
    id: str
    key: str
    summary: Optional[str] = None
    status_name: Optional[str] = None
    status_id: Optional[str] = None
    priority_name: Optional[str] = None
    issue_type_name: Optional[str] = None


class JiraIssueLinkModel(BaseModel):
    """Domain model for a Jira issue link"""
    id: str
    link_type: IssueLinkType
    direction: JiraIssueLinkDirection
    linked_issue: LinkedIssue

    @property
    def relationship_description(self) -> str:
        """Get the relationship description based on direction"""
        if self.direction == JiraIssueLinkDirection.INWARD:
            return self.link_type.inward_description
        return self.link_type.outward_description
