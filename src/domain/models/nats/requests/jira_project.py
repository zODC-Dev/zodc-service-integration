from pydantic import BaseModel


class JiraProjectSyncNATSRequestDTO(BaseModel):
    user_id: int
    project_key: str
    project_id: int
    jira_project_id: str
    sync_issues: bool = True
    sync_sprints: bool = True
    sync_users: bool = True
