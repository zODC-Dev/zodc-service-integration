from pydantic import BaseModel


class JiraAPIResponseBase(BaseModel):
    """Base class for all Jira API responses"""
    class Config:
        populate_by_name = True


class JiraAPIFieldsBase(JiraAPIResponseBase):
    """Base class for fields in Jira API responses"""
    pass
