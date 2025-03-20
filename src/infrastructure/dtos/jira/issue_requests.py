from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

# Base Request Models


class JiraAPIRequestBase(BaseModel):
    """Base class for all Jira API requests"""
    class Config:
        populate_by_name = True

# Issue Related Requests


class JiraAPICreateIssueFields(JiraAPIRequestBase):
    project: Dict[str, str] = Field(default_factory=dict)
    summary: str
    description: Optional[Dict[str, Any]] = None
    issuetype: Dict[str, str] = Field(default_factory=lambda: {"name": "Task"})
    assignee: Optional[Dict[str, str]] = Field(default=None)
    priority: Optional[Dict[str, str]] = Field(default=None)
    customfield_10016: Optional[float] = None  # Story points
    customfield_10017: Optional[float] = None  # Actual points


class JiraAPICreateIssueRequest(JiraAPIRequestBase):
    fields: JiraAPICreateIssueFields


class JiraAPIUpdateIssueFields(JiraAPIRequestBase):
    summary: Optional[str] = None
    description: Optional[Dict[str, Any]] = None
    assignee: Optional[Dict[str, str]] = None
    priority: Optional[Dict[str, str]] = None
    customfield_10016: Optional[float] = None
    customfield_10017: Optional[float] = None


class JiraAPIUpdateIssueRequest(JiraAPIRequestBase):
    fields: JiraAPIUpdateIssueFields
