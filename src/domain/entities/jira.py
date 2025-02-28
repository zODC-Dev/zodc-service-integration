from typing import Any, List, Optional, Dict

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

from src.domain.constants.jira import JiraIssueStatus, JiraIssueType, JiraSprintState


class JiraBaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allow both snake_case and camelCase input fields
        from_attributes=True
    )


class JiraAssignee(JiraBaseModel):
    account_id: str
    email_address: str
    avatar_url: str
    display_name: str


class JiraIssuePriority(JiraBaseModel):
    id: str
    icon_url: str
    name: str


class JiraIssueSprint(JiraBaseModel):
    id: int
    name: str
    state: JiraSprintState


class JiraIssue(JiraBaseModel):
    id: str
    key: str
    summary: str
    assignee: Optional[JiraAssignee] = None
    priority: Optional[JiraIssuePriority] = None
    type: JiraIssueType
    sprint: Optional[JiraIssueSprint] = None
    estimate_point: float = 0
    actual_point: Optional[float] = None
    description: Optional[str] = None
    created: str
    status: JiraIssueStatus
    updated: str

    @field_validator('description', mode='before')
    @classmethod
    def parse_description(cls, value: Optional[Any]) -> Optional[str]:
        if value is None:
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


class JiraProject(JiraBaseModel):
    id: str
    key: str
    name: str
    description: Optional[str] = None
    project_type: Optional[str] = None
    project_category: Optional[str] = None
    lead: Optional[str] = None
    url: Optional[str] = None
    avatar_url: Optional[str] = None
    is_jira_linked: bool = False


class JiraIssueCreate(BaseModel):
    project_key: str
    summary: str
    description: Optional[str] = None
    issue_type: str
    assignee: Optional[str] = None
    estimate_points: Optional[float] = None


class JiraIssueUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assignee: Optional[str] = None
    estimate_points: Optional[float] = None
    actual_points: Optional[float] = None


class JiraSprint(JiraBaseModel):
    id: int
    name: str
    state: JiraSprintState


class JiraUser(JiraBaseModel):
    display_name: str
    email_address: str
    account_id: str


class JiraIssueResponse(BaseModel):
    issue_id: str
    key: str
    self_url: str
