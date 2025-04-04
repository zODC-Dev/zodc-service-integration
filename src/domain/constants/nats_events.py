from enum import Enum


class NATSSubscribeTopic(str, Enum):
    USER_EVENT = "user.event"
    MICROSOFT_LOGIN = "microsoft.login"
    JIRA_LOGIN = "jira.login"
    JIRA_ISSUE_UPDATE = "jira.issue.update"
    JIRA_ISSUE_SYNC = "jira.issues.sync.request"
    USER_DEACTIVATED = "user.deactivated"
    USER_ACTIVATED = "user.activated"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_CREATED = "user.created"
    USER_LOGOUT = "user.logout"
    PROJECT_USERS_REQUEST = "project.users.request"
    JIRA_ISSUES_SYNC = "jira.issues.sync.request"
    JIRA_PROJECT_SYNC = "jira.project.sync.request"
    JIRA_ISSUE_LINK = "jira.issue.link.request"
    WORKFLOW_SYNC = "workflow.sync.request"


class NATSPublishTopic(str, Enum):
    PROJECT_USERS_RESPONSE = "project.users.response"
    JIRA_ISSUES_SYNC_RESULT = "jira.issues.sync.result"
    JIRA_ISSUE_SYNC_CONFLICT = "jira.issues.sync.conflict"
    JIRA_ISSUE_UPDATE_ERROR = "jira.issue.update.error"
    JIRA_PROJECT_SYNC_RESULT = "jira.project.sync.result"
