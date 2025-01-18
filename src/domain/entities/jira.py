from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator

from src.domain.constants.jira import JiraIssueType


class JiraTask(BaseModel):
    id: str
    key: str
    summary: str
    description: Optional[str] = None
    status: str
    assignee: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    priority: Optional[str] = None

    @field_validator('description', mode='before')
    @classmethod
    def parse_description(cls, value: Optional[Dict[str, Any]]) -> Optional[str]:
        if not value:
            return None

        # Handle Jira's Atlassian Document Format (ADF)
        if isinstance(value, dict):
            # Extract text content from ADF structure
            try:
                # Basic text extraction from content
                if 'content' in value:
                    text_parts = []
                    for content in value['content']:
                        if content.get('type') == 'paragraph':
                            for text_node in content.get('content', []):
                                if text_node.get('type') == 'text':
                                    text_parts.append(text_node.get('text', ''))
                    return ' '.join(text_parts)
                return None
            except Exception:
                return None

        # If it's already a string, return as is
        return str(value) if value else None


class JiraProject(BaseModel):
    id: str
    key: str
    name: str
    description: Optional[str] = None
    project_type: Optional[str] = None
    project_category: Optional[str] = None
    lead: Optional[str] = None
    url: Optional[str] = None


class JiraIssueCreate(BaseModel):
    project_key: str
    summary: str
    description: Optional[str] = None
    issue_type: JiraIssueType
    priority: Optional[str] = None
    assignee: Optional[str] = None
    labels: Optional[List[str]] = None
    epic_link: Optional[str] = None  # For linking to an epic
