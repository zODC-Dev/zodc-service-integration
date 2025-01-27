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


class JiraTaskStatus(Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"
    BLOCKED = "Blocked"
    CANCELLED = "Cancelled"

    def __str__(self) -> str:
        """Return the string representation of the issue type"""
        return self.value

    @classmethod
    def from_str(cls, status: str) -> "JiraTaskStatus":
        """Convert string status to enum value, case-insensitive"""
        for member in cls:
            if member.value.lower() == status.lower():
                return member
        raise ValueError(f"Invalid status: {status}")
