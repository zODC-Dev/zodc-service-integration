from enum import Enum


class NATSSubscribeTopic(str, Enum):
    USER_DEACTIVATED = "user.deactivated"
    USER_ACTIVATED = "user.activated"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_CREATED = "user.created"
    USER_LOGOUT = "user.logout"
    USER_JIRA_LOGIN = "jira.login"
    USER_MICROSOFT_LOGIN = "microsoft.login"
    PROJECT_LINKED = "project.linked"
    PROJECT_UNLINKED = "project.unlinked"
    PROJECT_USERS_REQUEST = "project.users.request"


class NATSPublishTopic(str, Enum):
    PROJECT_USERS_RESPONSE = "project.users.response"
