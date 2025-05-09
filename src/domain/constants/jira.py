from enum import Enum


class JiraIssueFieldId(str, Enum):
    """Enum cho các loại field trong Jira Issue"""
    STATUS = 'status'
    SPRINT = 'sprint'
    ASSIGNEE = 'assignee'
    STORY_POINTS = 'story_points'
    SUMMARY = 'summary'
    DESCRIPTION = 'description'
    REPORTER = 'reporter'


class JiraIssueType(Enum):
    TASK = "Task"
    STORY = "Story"
    EPIC = "Epic"
    BUG = "Bug"
    SUB_TASK = "Sub-task"

    def __str__(self) -> str:
        """Return the string representation of the issue type"""
        return self.value


class JiraIssueStatus(Enum):
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    TO_DO = "To Do"

    def __str__(self) -> str:
        """Return the string representation of the issue type"""
        return self.value

    @classmethod
    def from_str(cls, status: str) -> "JiraIssueStatus":
        """Convert string status to enum value, case-insensitive"""
        for member in cls:
            if member.value.lower() == status.lower():
                return member
        raise ValueError(f"Invalid status: {status}")


class JiraSprintState(Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    FUTURE = "future"

    def __str__(self) -> str:
        """Return the string representation of the sprint state"""
        return self.value

    @classmethod
    def from_str(cls, state: str) -> "JiraSprintState":
        """Convert string state to enum value, case-insensitive"""
        for member in cls:
            if member.value.lower() == state.lower():
                return member
        raise ValueError(f"Invalid state: {state}")


class JiraActionType(str, Enum):
    CREATE = "create"
    UPDATE = "update"


class JiraWebhookEvent(str, Enum):
    ISSUE_CREATED = "jira:issue_created"
    ISSUE_UPDATED = "jira:issue_updated"
    ISSUE_DELETED = "jira:issue_deleted"
    SPRINT_CREATED = "jira:sprint_created"
    SPRINT_UPDATED = "jira:sprint_updated"
    PROJECT_UPDATED = "jira:project_updated"
    SPRINT_STARTED = "jira:sprint_started"
    SPRINT_CLOSED = "jira:sprint_closed"
    USER_CREATED = "jira:user_created"
    USER_UPDATED = "jira:user_updated"
    USER_DELETED = "jira:user_deleted"
    SPRINT_DELETED = "jira:sprint_deleted"
