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
