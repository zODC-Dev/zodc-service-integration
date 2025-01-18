from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class JiraADFContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class JiraADFParagraph(BaseModel):
    type: Literal["paragraph"] = "paragraph"
    content: List[JiraADFContent]


class JiraADFDocument(BaseModel):
    type: Literal["doc"] = "doc"
    version: int = 1
    content: List[JiraADFParagraph]


class JiraProjectReference(BaseModel):
    key: str


class JiraIssueTypeReference(BaseModel):
    name: Literal["Task", "Bug", "Story", "Epic", "Subtask"]


class JiraUserReference(BaseModel):
    id: str  # accountId in Jira


class JiraPriorityReference(BaseModel):
    name: Literal["Highest", "High", "Medium", "Low", "Lowest"]


class JiraCreateIssueFields(BaseModel):
    project: JiraProjectReference
    summary: str
    issuetype: JiraIssueTypeReference
    description: JiraADFDocument
    priority: Optional[JiraPriorityReference] = None
    assignee: Optional[JiraUserReference] = None
    labels: Optional[List[str]] = None


class JiraCreateIssueRequest(BaseModel):
    fields: JiraCreateIssueFields


class JiraIssueStatus(BaseModel):
    name: str


class JiraUser(BaseModel):
    display_name: str = Field(alias="displayName")
    account_id: str = Field(alias="accountId")


class JiraIssuePriority(BaseModel):
    name: str
    id: str


class JiraIssueFields(BaseModel):
    summary: str
    description: Optional[JiraADFDocument] = None
    status: JiraIssueStatus
    assignee: Optional[JiraUser] = None
    created: str  # datetime string
    updated: str  # datetime string
    priority: Optional[JiraIssuePriority] = None


class JiraIssueResponse(BaseModel):
    id: str
    key: str
    fields: JiraIssueFields


class JiraCreateIssueResponse(BaseModel):
    id: str
    key: str
    self: str  # API URL of the created issue
