from typing import Optional

from src.app.schemas.responses.base import BaseResponse
from src.domain.models.jira_project import JiraProjectModel
from src.domain.models.jira_sprint import JiraSprintModel


class GetJiraProjectResponse(BaseResponse):
    id: Optional[str] = None
    key: str
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    is_system_linked: bool = False

    @classmethod
    def from_domain(cls, project: JiraProjectModel) -> "GetJiraProjectResponse":
        return cls(
            id=project.jira_project_id,
            key=project.key,
            name=project.name,
            description=project.description,
            avatar_url=project.avatar_url,
            is_system_linked=project.is_system_linked
        )


class GetJiraSprintResponse(BaseResponse):
    id: int
    name: str
    state: str  # active, closed, future
    is_current: bool = False

    @classmethod
    def from_domain(cls, sprint: JiraSprintModel) -> "GetJiraSprintResponse":
        return cls(
            id=sprint.id,
            name=sprint.name,
            state=sprint.state,
            is_current=sprint.is_current
        )
