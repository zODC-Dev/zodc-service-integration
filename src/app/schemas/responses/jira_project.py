from typing import Optional

from pydantic import BaseModel, Field

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
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    complete_date: Optional[str] = None
    is_current: bool = False

    @classmethod
    def from_domain(cls, sprint: JiraSprintModel) -> "GetJiraSprintResponse":
        return cls(
            id=sprint.id,
            name=sprint.name,
            state=sprint.state,
            start_date=sprint.start_date.isoformat() if sprint.start_date else None,
            end_date=sprint.end_date.isoformat() if sprint.end_date else None,
            complete_date=sprint.complete_date.isoformat() if sprint.complete_date else None,
            is_current=sprint.is_current
        )


class TaskCountByStatus(BaseModel):
    to_do: int = Field(alias="toDo")
    in_progress: int = Field(alias="inProgress")
    done: int = Field(alias="done")

    class Config:
        populate_by_name = True


class GetJiraSprintDetailsResponse(BaseResponse):
    id: int
    name: str
    state: str  # active, closed, future
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    complete_date: Optional[str] = None
    goal: Optional[str] = None
    is_current: bool = False
    task_count_by_status: TaskCountByStatus = Field(alias="taskCountByStatus")
    total_tasks: int = 0

    @classmethod
    def from_domain(cls, sprint: JiraSprintModel, task_count_by_status: TaskCountByStatus) -> "GetJiraSprintDetailsResponse":
        total_tasks = task_count_by_status.to_do + task_count_by_status.in_progress + task_count_by_status.done
        return cls(
            id=sprint.id,
            name=sprint.name,
            state=sprint.state,
            start_date=sprint.start_date.isoformat() if sprint.start_date else None,
            end_date=sprint.end_date.isoformat() if sprint.end_date else None,
            complete_date=sprint.complete_date.isoformat() if sprint.complete_date else None,
            goal=sprint.goal,
            is_current=sprint.is_current,
            task_count_by_status=task_count_by_status,
            total_tasks=total_tasks
        )
