from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class JiraADFContentAPIModel(BaseModel):
    type: Literal["text"] = "text"
    text: str


class JiraADFParagraphAPIModel(BaseModel):
    type: Literal["paragraph"] = "paragraph"
    content: List[JiraADFContentAPIModel]


class JiraADFDocumentAPIModel(BaseModel):
    type: Literal["doc"] = "doc"
    version: int = 1
    content: List[JiraADFParagraphAPIModel]


class JiraProjectReferenceAPIModel(BaseModel):
    key: str


class JiraIssueTypeReferenceAPIModel(BaseModel):
    name: Literal["Task", "Bug", "Story", "Epic", "Subtask"]


class JiraUserReferenceAPIModel(BaseModel):
    id: str  # accountId in Jira


class JiraIssuePriorityReferenceAPIModel(BaseModel):
    name: Literal["Highest", "High", "Medium", "Low", "Lowest"]


class JiraCreateIssueFieldsAPIModel(BaseModel):
    project: JiraProjectReferenceAPIModel
    summary: str
    issuetype: JiraIssueTypeReferenceAPIModel
    description: JiraADFDocumentAPIModel
    priority: Optional[JiraIssuePriorityReferenceAPIModel] = None
    assignee: Optional[JiraUserReferenceAPIModel] = None
    labels: Optional[List[str]] = None


class JiraCreateIssueRequestAPIModel(BaseModel):
    fields: JiraCreateIssueFieldsAPIModel


class JiraIssueStatusAPIModel(BaseModel):
    name: str


class JiraUserAPIModel(BaseModel):
    display_name: str = Field(alias="displayName")
    account_id: str = Field(alias="accountId")


class JiraIssuePriorityAPIModel(BaseModel):
    name: str
    id: str


class JiraIssueFieldsAPIModel(BaseModel):
    summary: str
    description: Optional[JiraADFDocumentAPIModel] = None
    status: JiraIssueStatusAPIModel
    assignee: Optional[JiraUserAPIModel] = None
    created: str  # datetime string
    updated: str  # datetime string
    priority: Optional[JiraIssuePriorityAPIModel] = None
