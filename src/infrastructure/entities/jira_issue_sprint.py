from datetime import datetime, timezone

from sqlmodel import Column, DateTime, Field, SQLModel


class JiraIssueSprintEntity(SQLModel, table=True):
    __tablename__ = "jira_issue_sprints"

    jira_issue_id: str = Field(foreign_key="jira_issues.jira_issue_id", primary_key=True)
    jira_sprint_id: int = Field(foreign_key="jira_sprints.jira_sprint_id", primary_key=True)

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True)),
        default_factory=lambda: datetime.now(timezone.utc)
    )
