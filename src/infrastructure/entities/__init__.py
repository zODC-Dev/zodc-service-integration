from .base import BaseEntity, BaseEntityWithTimestamps
from .jira_issue import JiraIssueEntity
from .jira_issue_history import JiraIssueHistoryEntity
from .jira_issue_sprint import JiraIssueSprintEntity
from .jira_project import JiraProjectEntity
from .jira_sprint import JiraSprintEntity
from .jira_user import JiraUserEntity
from .media import MediaEntity
from .refresh_token import RefreshTokenEntity
from .sync_log import SyncLogEntity
from .system_config import SystemConfigEntity

# Update forward references
BaseEntity.model_rebuild()
BaseEntityWithTimestamps.model_rebuild()
RefreshTokenEntity.model_rebuild()
JiraProjectEntity.model_rebuild()
JiraUserEntity.model_rebuild()
JiraIssueEntity.model_rebuild()
JiraSprintEntity.model_rebuild()
JiraIssueSprintEntity.model_rebuild()
JiraIssueHistoryEntity.model_rebuild()
SyncLogEntity.model_rebuild()
MediaEntity.model_rebuild()
SystemConfigEntity.model_rebuild()
