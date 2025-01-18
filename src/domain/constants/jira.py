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
