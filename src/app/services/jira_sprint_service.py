from datetime import datetime, timedelta
import re
from typing import Optional

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.schemas.responses.jira_project import TaskCountByStatus
from src.configs.logger import log
from src.domain.constants.jira import JiraIssueStatus, JiraSprintState
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


class JiraSprintApplicationService:
    """Application service for Jira sprint operations"""

    def __init__(
        self,
        jira_sprint_api_service: IJiraSprintAPIService,
        jira_sprint_database_service: IJiraSprintDatabaseService,
        jira_issue_repository: IJiraIssueRepository
    ):
        self.jira_sprint_api_service = jira_sprint_api_service
        self.jira_sprint_database_service = jira_sprint_database_service
        self.jira_issue_repository = jira_issue_repository

    async def get_current_sprint(
        self,
        session: AsyncSession,
        project_key: str
    ) -> Optional[JiraSprintModel]:
        """Get the current sprint in Jira"""
        return await self.jira_sprint_database_service.get_current_sprint(session=session, project_key=project_key)

    async def start_sprint(
        self,
        session: AsyncSession,
        sprint_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        goal: Optional[str] = None
    ) -> Optional[JiraSprintModel]:
        """Start a sprint in Jira using admin account

        Args:
            session: AsyncSession
            sprint_id: ID of the sprint to start
            start_date: Optional start date for the sprint (default: current date)
            end_date: Optional end date for the sprint (default: start_date + 14 days)
            goal: Optional goal for the sprint
        """
        # Get sprint from database
        sprint = await self.jira_sprint_database_service.get_sprint_by_id(session=session, sprint_id=sprint_id)
        if sprint is None:
            return None

        # Use default values if not provided
        if start_date is None:
            start_date = datetime.now()

        if end_date is None:
            end_date = start_date + timedelta(days=14)

        # Start the sprint in Jira with the provided dates and goal
        await self.jira_sprint_api_service.start_sprint_with_admin_auth(
            sprint_id=sprint.jira_sprint_id,
            start_date=start_date,
            end_date=end_date,
            goal=goal
        )

        # Update the sprint model with the new values
        sprint.state = JiraSprintState.ACTIVE.value
        sprint.start_date = start_date
        sprint.end_date = end_date
        if goal is not None:
            sprint.goal = goal

        return sprint

    async def end_sprint(
        self,
        session: AsyncSession,
        sprint_id: int
    ) -> Optional[JiraSprintModel]:
        """End a sprint in Jira using admin account"""
        # Get sprint from database
        sprint = await self.jira_sprint_database_service.get_sprint_by_id(session=session, sprint_id=sprint_id)
        if sprint is None:
            return None

        # End sprint in Jira
        await self.jira_sprint_api_service.end_sprint_with_admin_auth(sprint_id=sprint.jira_sprint_id)
        sprint.state = JiraSprintState.CLOSED.value

        # Reset is_system_linked flag for all issues in this sprint
        try:
            updated_count = await self.jira_issue_repository.reset_system_linked_for_sprint(
                session=session,
                sprint_id=sprint_id
            )
            log.info(f"Reset is_system_linked flag for {updated_count} issues in sprint {sprint_id}")
        except Exception as e:
            log.error(f"Error resetting is_system_linked flag for issues in sprint {sprint_id}: {str(e)}")

        # Create a new future sprint after ending the current one
        await self.create_sprint(sprint)

        return sprint

    async def get_sprint_details(
        self,
        session: AsyncSession,
        sprint_id: int
    ) -> tuple[Optional[JiraSprintModel], TaskCountByStatus]:
        """Get sprint details with tasks by status"""
        # Get sprint from database
        sprint = await self.jira_sprint_database_service.get_sprint_by_id(session=session, sprint_id=sprint_id)
        if sprint is None:
            return None, {}

        assert sprint.project_key is not None, "Sprint must have a project key"
        # Get all issues for this sprint
        issues = await self.jira_issue_repository.get_project_issues(
            session=session,
            project_key=sprint.project_key,
            sprint_id=sprint_id,
            include_deleted=False
        )

        # Count issues by status
        task_count_by_status = TaskCountByStatus(
            to_do=0,
            in_progress=0,
            done=0
        )

        for issue in issues:
            # Map Jira statuses to simplified status categories
            if issue.status in [JiraIssueStatus.TO_DO]:
                task_count_by_status.to_do += 1
            elif issue.status in [JiraIssueStatus.IN_PROGRESS]:
                task_count_by_status.in_progress += 1
            elif issue.status in [JiraIssueStatus.DONE]:
                task_count_by_status.done += 1

        return sprint, task_count_by_status

    async def create_sprint(self, old_sprint: JiraSprintModel) -> Optional[int]:
        """Create a new sprint in Jira"""
        # Create a new future sprint after ending the current one
        try:
            # Calculate next sprint number from current sprint name if possible
            current_sprint_name = old_sprint.name
            next_sprint_name = current_sprint_name

            assert old_sprint.project_key is not None, "Project key is required to create a new sprint"

            # Try to extract sprint number and increment it
            # Current sprint name is in the format "PROJECT Sprint X"
            sprint_number_match = re.search(rf'{old_sprint.project_key} Sprint\s+(\d+)',
                                            current_sprint_name, re.IGNORECASE)
            if sprint_number_match:
                current_number = int(sprint_number_match.group(1))
                next_number = current_number + 1
                next_sprint_name = f"{old_sprint.project_key} Sprint {next_number}"

            else:
                next_sprint_name = f"{old_sprint.project_key} Sprint 1"

            # Create new sprint in Jira
            # Log the next sprint name
            log.debug(
                f"Creating new sprint '{next_sprint_name}' in Jira, board_id: {old_sprint.board_id}, project_key: {old_sprint.project_key}")

            # assert board id is not None, since last sprint must have a board id
            assert old_sprint.board_id is not None, "Last sprint must have a board id"

            new_sprint_jira_id = await self.jira_sprint_api_service.create_sprint_with_admin_auth(
                name=next_sprint_name,
                board_id=old_sprint.board_id,
                project_key=old_sprint.project_key
            )

            log.debug(f"Created new future sprint '{next_sprint_name}' with Jira ID {new_sprint_jira_id}")
            return new_sprint_jira_id
        except Exception as e:
            log.error(f"Error creating new future sprint after ending sprint {old_sprint.id}: {str(e)}")
            # Don't fail the main operation if creating a new sprint fails
            return None
