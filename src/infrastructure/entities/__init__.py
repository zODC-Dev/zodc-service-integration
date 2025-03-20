from .base import BaseEntity, BaseEntityWithTimestamps
from .jira_issue import JiraIssueEntity
from .jira_project import JiraProjectEntity
from .jira_user import JiraUserEntity
from .refresh_token import RefreshTokenEntity

# Update forward references
BaseEntity.model_rebuild()
BaseEntityWithTimestamps.model_rebuild()
RefreshTokenEntity.model_rebuild()
JiraProjectEntity.model_rebuild()
JiraUserEntity.model_rebuild()
JiraIssueEntity.model_rebuild()
