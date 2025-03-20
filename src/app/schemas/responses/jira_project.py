from typing import Optional

from src.app.schemas.responses.base import BaseResponse
from src.domain.models.jira_project import JiraProjectModel


class GetJiraProjectResponse(BaseResponse):
    id: Optional[int] = None
    key: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    is_jira_linked: bool = False

    @classmethod
    def from_domain(cls, project: JiraProjectModel) -> "GetJiraProjectResponse":
        return cls(
            id=project.id,
            key=project.key,
            name=project.name,
            description=project.description,
            avatar_url=project.avatar_url,
            is_jira_linked=project.is_jira_linked
        )


class GetJiraSprintResponse(BaseResponse):
    id: int
    name: str
    state: str  # active, closed, future
