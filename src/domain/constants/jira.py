from enum import Enum


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
    IN_REVIEW = "In Review"
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


# Status ID mapping - cần cập nhật các ID tương ứng với Jira instance của bạn
JIRA_STATUS_ID_MAPPING = {
    "10014": JiraIssueStatus.TO_DO,
    "10015": JiraIssueStatus.IN_PROGRESS,
    "10002": JiraIssueStatus.IN_REVIEW,
    "10016": JiraIssueStatus.DONE,
}

# Issue Type ID mapping
JIRA_ISSUE_TYPE_ID_MAPPING = {
    "10009": JiraIssueType.TASK,
    "10011": JiraIssueType.STORY,
    "10002": JiraIssueType.EPIC,
    "10010": JiraIssueType.BUG,
    "10004": JiraIssueType.SUB_TASK,
}


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
