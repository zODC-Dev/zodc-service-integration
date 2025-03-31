from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Column, DateTime, Field, ForeignKey, Relationship, SQLModel, String, Text

if TYPE_CHECKING:
    from src.infrastructure.entities.jira_issue import JiraIssueEntity
    from src.infrastructure.entities.jira_user import JiraUserEntity


class JiraIssueHistoryEntity(SQLModel, table=True):
    """Entity để lưu trữ lịch sử thay đổi của Jira issue"""
    __tablename__ = "jira_issue_histories"  # Chú ý tên bảng số nhiều

    id: int = Field(default=None, primary_key=True)
    # Chú ý đây là string, không phải integer
    jira_issue_id: str = Field(
        sa_column=Column(String, ForeignKey("jira_issues.jira_issue_id", name="fk_jira_issues"), nullable=False)
    )
    field_name: str = Field(max_length=100, nullable=False)
    field_type: str = Field(max_length=50, nullable=True)
    old_value: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    new_value: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    old_string: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    new_string: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    # Chú ý author_id trỏ tới jira_account_id trong bảng jira_users
    author_id: Optional[str] = Field(
        sa_column=Column(String, ForeignKey("jira_users.jira_account_id", name="fk_jira_users"), nullable=True)
    )
    created_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    jira_change_id: Optional[str] = Field(max_length=100, nullable=True)

    # Định nghĩa mối quan hệ với JiraIssueEntity và JiraUserEntity
    issue: Optional["JiraIssueEntity"] = Relationship(
        back_populates="histories",
        sa_relationship_kwargs={"lazy": "joined"}
    )

    author: Optional["JiraUserEntity"] = Relationship(
        back_populates="issue_histories",
        sa_relationship_kwargs={"lazy": "joined"}
    )

    # def __repr__(self):
    #     """String representation of the JiraIssueHistoryEntity"""
    #     return f"<JiraIssueHistory(id={self.id}, issue_id={self.issue_id}, field={self.field_name})>"
