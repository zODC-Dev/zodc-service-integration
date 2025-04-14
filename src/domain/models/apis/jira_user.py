from typing import Optional

from pydantic import BaseModel
from pydantic.alias_generators import to_camel

from src.domain.models.jira_user import JiraUserModel


class JiraAssigneeResponse(BaseModel):
    id: Optional[int] = None
    jira_account_id: str
    email: str
    avatar_url: Optional[str] = None
    name: str
    is_system_user: bool

    class Config:
        populate_by_name = True
        alias_generator = to_camel

    @classmethod
    def from_domain(cls, assignee: JiraUserModel) -> "JiraAssigneeResponse":
        return cls(
            id=assignee.user_id,
            jira_account_id=assignee.jira_account_id,
            email=assignee.email,
            avatar_url=assignee.avatar_url,
            name=assignee.name,
            is_system_user=assignee.is_system_user
        )
