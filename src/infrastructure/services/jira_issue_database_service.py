from datetime import datetime, timezone
from typing import List, Optional

from src.domain.constants.jira import JiraIssueType
from src.domain.models.database.jira_issue import JiraIssueDBCreateDTO, JiraIssueDBUpdateDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService


class JiraIssueDatabaseService(IJiraIssueDatabaseService):
    def __init__(
        self,
        issue_repository: IJiraIssueRepository,
    ):
        self.issue_repository = issue_repository

    async def get_issue(self, user_id: int, issue_id: str) -> Optional[JiraIssueModel]:
        """Get issue from database by ID"""
        return await self.issue_repository.get_by_jira_issue_id(issue_id)

    async def create_issue(self, user_id: int, issue: JiraIssueDBCreateDTO) -> JiraIssueModel:
        """Create a new issue in database"""
        return await self.issue_repository.create(issue)

    async def update_issue(
        self,
        user_id: int,
        issue_id: str,
        update: JiraIssueDBUpdateDTO
    ) -> JiraIssueModel:
        """Update an existing issue in database"""
        current_issue = await self.issue_repository.get_by_jira_issue_id(issue_id)
        if not current_issue:
            raise ValueError(f"Issue {issue_id} not found in database")

        # Update fields
        if update.summary:
            current_issue.summary = update.summary
        if update.description:
            current_issue.description = update.description
        if update.assignee:
            current_issue.assignee_id = update.assignee
        if update.estimate_point is not None:
            current_issue.estimate_point = update.estimate_point
        if update.actual_point is not None:
            current_issue.actual_point = update.actual_point
        if update.status:
            current_issue.status = update.status

        current_issue.updated_at = datetime.now(timezone.utc)
        # current_issue.needs_sync = True  # Mark as needing sync with Jira

        return await self.issue_repository.update(issue_id, JiraIssueDBUpdateDTO.model_validate(current_issue))

    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[int] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        """Get project issues from database with filters"""
        return await self.issue_repository.get_project_issues(
            project_key=project_key,
            sprint_id=sprint_id,
            is_backlog=is_backlog,
            issue_type=issue_type,
            search=search,
            limit=limit
        )
