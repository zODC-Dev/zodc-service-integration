import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypeVar

from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.services.jira_issue_history_service import JiraIssueHistoryApplicationService
from src.configs.logger import log
from src.domain.constants.jira import JiraIssueType
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.exceptions.jira_exceptions import JiraRequestError
from src.domain.models.database.jira_issue import JiraIssueDBCreateDTO, JiraIssueDBUpdateDTO
from src.domain.models.database.jira_issue_history import JiraIssueHistoryDBCreateDTO
from src.domain.models.database.jira_project import JiraProjectDBCreateDTO, JiraProjectDBUpdateDTO
from src.domain.models.database.jira_sprint import JiraSprintDBCreateDTO, JiraSprintDBUpdateDTO
from src.domain.models.database.jira_user import JiraUserDBCreateDTO, JiraUserDBUpdateDTO
from src.domain.models.database.sync_log import SyncLogDBCreateDTO
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_project import JiraProjectModel
from src.domain.models.jira_sprint import JiraSprintModel
from src.domain.models.jira_user import JiraUserModel
from src.domain.models.nats.replies.jira_project import (
    JiraProjectSyncNATSReplyDTO,
    JiraProjectSyncSummaryDTO,
    SyncedJiraUserDTO,
)
from src.domain.models.nats.requests.jira_project import JiraProjectSyncNATSRequestDTO
from src.domain.repositories.jira_issue_history_repository import IJiraIssueHistoryRepository
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_project_database_service import IJiraProjectDatabaseService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService

T = TypeVar('T')


class JiraProjectApplicationService:
    def __init__(
        self,
        jira_project_api_service: IJiraProjectAPIService,
        jira_project_db_service: IJiraProjectDatabaseService,
        jira_issue_db_service: IJiraIssueDatabaseService,
        jira_sprint_db_service: IJiraSprintDatabaseService,
        jira_issue_api_service: IJiraIssueAPIService,
        jira_issue_history_service: JiraIssueHistoryApplicationService,
        sync_log_repository: ISyncLogRepository,
        jira_project_repository: IJiraProjectRepository,
        jira_issue_repository: IJiraIssueRepository,
        jira_sprint_repository: IJiraSprintRepository,
        jira_user_repository: IJiraUserRepository,
        jira_issue_history_repository: IJiraIssueHistoryRepository
    ):
        self.jira_project_api_service = jira_project_api_service
        self.jira_project_db_service = jira_project_db_service
        self.jira_issue_db_service = jira_issue_db_service
        self.jira_sprint_db_service = jira_sprint_db_service
        self.sync_log_repository = sync_log_repository
        self.jira_issue_api_service = jira_issue_api_service
        self.jira_issue_history_service = jira_issue_history_service
        self.jira_project_repository = jira_project_repository
        self.jira_issue_repository = jira_issue_repository
        self.jira_sprint_repository = jira_sprint_repository
        self.jira_user_repository = jira_user_repository
        self.jira_issue_history_repository = jira_issue_history_repository

    async def get_project_issues(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        sprint_id: Optional[int] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        return await self.jira_issue_db_service.get_project_issues(
            session=session,
            user_id=user_id,
            project_key=project_key,
            sprint_id=sprint_id,
            is_backlog=is_backlog,
            issue_type=issue_type,
            search=search,
            limit=limit
        )

    async def get_accessible_projects(self, session: AsyncSession, user_id: int) -> List[JiraProjectModel]:
        """Get projects from Jira API and merge with database data"""
        try:
            # Get projects from database first
            db_projects = await self.jira_project_db_service.get_all_projects(session=session)
            db_projects_dict = {project.key: project for project in db_projects}

            # Get projects from Jira API
            jira_projects = await self.jira_project_api_service.get_accessible_projects(
                session=session,
                user_id=user_id
            )

            # Merge data
            merged_projects = []
            for jira_project in jira_projects:
                project = jira_project
                # Check if project exists in database
                if jira_project.key in db_projects_dict:
                    db_project = db_projects_dict[jira_project.key]
                    project.is_system_linked = True
                    project.id = db_project.id  # Preserve database ID if exists
                else:
                    project.is_system_linked = False

                merged_projects.append(project)

            return merged_projects

        except Exception as e:
            log.error(f"Error getting accessible projects: {str(e)}")
            raise JiraRequestError(500, str(e)) from e

    async def get_project_sprints(
        self,
        session: AsyncSession,
        project_key: str,
    ) -> List[JiraSprintModel]:
        # Sprints are always fetched from database as they already synced
        sprints = await self.jira_sprint_db_service.get_project_sprints(
            session=session,
            project_key=project_key
        )
        return sprints

    async def get_project_by_key(self, session: AsyncSession, key: str) -> Optional[JiraProjectModel]:
        """Get project from database by key"""
        return await self.jira_project_db_service.get_project_by_key(session=session, key=key)

    async def update_project(
        self,
        session: AsyncSession,
        project_id: int,
        project_data: JiraProjectDBUpdateDTO
    ) -> JiraProjectModel:
        """Update project in database"""
        return await self.jira_project_db_service.update_project(session=session, project_id=project_id, project_data=project_data)

    async def sync_project(self, session: AsyncSession, request: JiraProjectSyncNATSRequestDTO) -> JiraProjectSyncNATSReplyDTO:
        try:
            log.info(f"Starting sync for project {request.project_key}")
            started_at = datetime.now(timezone.utc)
            synced_users = []
            initial_log_data = None

            # Prepare log data but don't create it yet
            initial_log_data = SyncLogDBCreateDTO(
                entity_type=EntityType.PROJECT,
                entity_id=request.project_key,
                operation=OperationType.SYNC,
                source=SourceType.NATS,
                sender=request.user_id,
                request_payload={"project_key": request.project_key,
                                 "user_id": request.user_id, "project_id": request.project_id},
            )

            try:
                # Create the initial log within the session context
                if initial_log_data:
                    await self.sync_log_repository.create_sync_log(session, initial_log_data)

                # Sync project details
                log.info("Syncing project details...")
                project = await self._sync_project_details(session, request.user_id, request.project_key, request.project_id)

                # Sync project users
                log.info("Syncing project users...")
                users = await self._sync_project_users(session, request.user_id, request.project_key)
                log.info(f"Successfully synced {len(users)} users")

                # Prepare synced users for response
                synced_users = [
                    SyncedJiraUserDTO(
                        id=user.id,
                        jira_account_id=user.jira_account_id,
                        name=user.name,
                        email=user.email,
                        is_active=user.is_active,
                        avatar_url=user.avatar_url
                    ) for user in users
                ]

                # Sync sprints
                log.info("Syncing project sprints...")
                sprint_id_mapping = await self._sync_project_sprints(session, request.user_id, request.project_key)
                log.info(f"Successfully synced {len(sprint_id_mapping)} sprints")

                # Sync issues
                log.info("Syncing project issues...")
                issues = await self._sync_project_issues(session, request.user_id, request.project_key)
                log.info(f"Successfully synced {len(issues)} issues")

                # Sync changelog
                log.info("Syncing project changelog...")
                issue_ids = [issue.jira_issue_id for issue in issues]
                log.info(f"Syncing changelog for {len(issue_ids)} issues")
                # issue_ids = ['10383', '10382', '10381', '10380', '10379']
                await self._sync_project_changelog(session, issue_ids)

                # Create success log
                success_log_data = SyncLogDBCreateDTO(
                    entity_type=EntityType.PROJECT,
                    entity_id=project.key,
                    operation=OperationType.SYNC,
                    source=SourceType.NATS,
                    sender=request.user_id,
                    request_payload={"project_key": project.key, "project_id": project.id},
                    response_status=200,
                    response_body={"project_id": project.id, "project_key": project.key},
                )
                await self.sync_log_repository.create_sync_log(session, success_log_data)
                log.info(f"Successfully completed sync for project {request.project_key}")

                return JiraProjectSyncNATSReplyDTO(
                    success=True,
                    project_key=request.project_key,
                    sync_summary=JiraProjectSyncSummaryDTO(
                        started_at=started_at.isoformat(),
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        total_sprints=len(sprint_id_mapping) if 'sprint_id_mapping' in locals() else 0,
                        total_issues=len(issues) if 'issues' in locals() else 0,
                        total_users=len(users) if 'users' in locals() else 0,
                        synced_users=len(synced_users)
                    ),
                    synced_users=synced_users
                )

            except Exception as e:
                log.error(f"Error during sync operations: {str(e)}")
                # Create error log
                try:
                    error_log_data = SyncLogDBCreateDTO(
                        entity_type=EntityType.PROJECT,
                        entity_id=request.project_key,
                        operation=OperationType.SYNC,
                        source=SourceType.NATS,
                        sender=request.user_id,
                        request_payload={"project_key": request.project_key, "user_id": request.user_id},
                        error_message=str(e),
                    )
                    await self.sync_log_repository.create_sync_log(session, error_log_data)
                except Exception as log_error:
                    log.error(f"Failed to create error log: {str(log_error)}")

                # Propagate the original error - but don't manage the transaction here,
                # let the caller handle it
                raise

        except Exception as e:
            log.error(f"Error during project sync: {str(e)}")
            raise

    async def _sync_project_details(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str,
        project_id: int
    ) -> JiraProjectModel:
        try:
            # Fetch from Jira API
            project_details = await self.jira_project_api_service.get_project_details(
                session=session,
                user_id=user_id,
                project_key=project_key
            )

            # Check if project exists
            existing_project = await self.jira_project_repository.get_project_by_key(
                session=session,
                key=project_key
            )

            if existing_project and existing_project.id:
                # Update existing project
                update_dto = JiraProjectDBUpdateDTO(
                    project_id=project_id,
                    name=project_details.name,
                    avatar_url=project_details.avatar_url,
                    description=project_details.description,
                    is_system_linked=True
                )
                return await self.jira_project_repository.update_project(
                    session=session,
                    project_id=existing_project.id,
                    project_data=update_dto
                )
            else:
                # Create new project
                create_dto = JiraProjectDBCreateDTO(
                    project_id=project_id,
                    jira_project_id=project_details.jira_project_id,
                    key=project_details.key,
                    name=project_details.name,
                    description=project_details.description,
                    avatar_url=project_details.avatar_url,
                    is_system_linked=True,
                    user_id=user_id
                )
                return await self.jira_project_repository.create_project(
                    session=session,
                    project_data=create_dto
                )

        except Exception as e:
            log.error(f"Error syncing project details: {str(e)}", exc_info=True)
            raise

    async def _sync_project_users(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str
    ) -> List[JiraUserModel]:
        """Sync project users from Jira API to database"""
        try:
            # Fetch users from Jira API
            jira_users = await self.jira_project_api_service.get_project_users(
                session=session,
                user_id=user_id,
                project_key=project_key
            )

            synced_users = []
            for jira_user in jira_users:
                try:
                    assert jira_user.jira_account_id is not None, "Jira account ID is required"
                    # Check if user exists by jira_account_id
                    existing_user = await self.jira_user_repository.get_user_by_jira_account_id(
                        session=session,
                        jira_account_id=jira_user.jira_account_id
                    )

                    if existing_user and existing_user.jira_account_id:
                        # Update existing user if needed
                        update_dto = JiraUserDBUpdateDTO(
                            # email=jira_user.email,
                            avatar_url=jira_user.avatar_url,
                            is_active=jira_user.is_active,
                        )
                        await self.jira_user_repository.update_user_by_jira_account_id(
                            session=session,
                            jira_account_id=existing_user.jira_account_id,
                            user_data=update_dto
                        )
                        synced_users.append(existing_user)
                    else:
                        # Create new user only if they don't exist
                        create_dto = JiraUserDBCreateDTO(
                            jira_account_id=jira_user.jira_account_id,
                            name=jira_user.name,
                            is_active=jira_user.is_active,
                            email=jira_user.email,
                            avatar_url=jira_user.avatar_url,
                            is_system_user=False
                        )
                        new_user = await self.jira_user_repository.create_user(
                            session=session,
                            user_data=create_dto
                        )
                        synced_users.append(new_user)

                except Exception as e:
                    log.error(f"Error syncing user {jira_user.jira_account_id}: {str(e)}")
                    # Continue with next user even if one fails
                    continue

            return synced_users

        except Exception as e:
            log.error(f"Error syncing project users: {str(e)}")
            raise

    async def _sync_project_sprints(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str
    ) -> dict[int, int]:
        sprint_id_mapping: Dict[int, int] = {}
        sprints = await self.jira_project_api_service.get_project_sprints(
            session=session,
            user_id=user_id,
            project_key=project_key
        )

        for sprint in sprints:
            try:
                # Check if sprint exists by jira_sprint_id
                existing_sprint = await self.jira_sprint_repository.get_sprint_by_jira_sprint_id(
                    session=session,
                    jira_sprint_id=sprint.jira_sprint_id
                )

                sprint_data = JiraSprintDBCreateDTO(
                    jira_sprint_id=sprint.jira_sprint_id,
                    name=sprint.name,
                    state=sprint.state,
                    start_date=sprint.start_date,
                    end_date=sprint.end_date,
                    complete_date=sprint.complete_date,
                    goal=sprint.goal,
                    project_key=project_key,
                    board_id=sprint.board_id
                )

                if existing_sprint and existing_sprint.id:
                    # Update if exists
                    updated_sprint = await self.jira_sprint_repository.update_sprint(
                        session=session,
                        sprint_id=existing_sprint.id,
                        sprint_data=JiraSprintDBUpdateDTO(**sprint_data.model_dump())
                    )
                    if updated_sprint and updated_sprint.id:
                        sprint_id_mapping[sprint.jira_sprint_id] = updated_sprint.id
                else:
                    # Create new if not exists
                    new_sprint = await self.jira_sprint_repository.create_sprint(
                        session=session,
                        sprint_data=sprint_data
                    )
                    if new_sprint and new_sprint.id:
                        sprint_id_mapping[sprint.jira_sprint_id] = new_sprint.id

            except Exception as e:
                log.error(f"Error syncing sprint {sprint.jira_sprint_id}: {str(e)}")
                continue

        return sprint_id_mapping

    async def _sync_project_issues(
        self,
        session: AsyncSession,
        user_id: int,
        project_key: str
    ) -> List[JiraIssueModel]:
        """Sync all project issues from Jira API to database"""
        try:
            jira_issues = await self.jira_project_api_service.get_project_issues(
                session=session,
                user_id=user_id,
                project_key=project_key,
                limit=1000
            )

            synced_issues = []
            for jira_issue in jira_issues:
                try:
                    # Map the issue to domain model
                    # mapped_issue = JiraIssueMapper.to_domain_issue(jira_issue)

                    # Check if issue exists
                    existing_issue = await self.jira_issue_repository.get_by_jira_issue_id(
                        session=session,
                        jira_issue_id=jira_issue.jira_issue_id
                    )

                    if existing_issue:
                        if jira_issue.updated_at > existing_issue.last_synced_at:
                            # Update existing issue with new data
                            updated_issue = await self.jira_issue_repository.update(
                                session=session,
                                issue_id=existing_issue.jira_issue_id,
                                issue_update=JiraIssueDBUpdateDTO._from_domain(jira_issue)
                            )
                            synced_issues.append(updated_issue)
                    else:
                        # Create new issue
                        issue_create_dto = JiraIssueDBCreateDTO._from_domain(jira_issue)
                        new_issue = await self.jira_issue_repository.create(
                            session=session,
                            issue=issue_create_dto
                        )
                        synced_issues.append(new_issue)

                except Exception as e:
                    log.error(f"Error syncing issue {jira_issue.key}: {str(e)}")
                    # Don't abort the whole transaction if one issue fails
                    continue

            return synced_issues

        except Exception as e:
            log.error(f"Error syncing project issues: {str(e)}")
            raise

    async def _fetch_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0
    ) -> T:
        """Retry a function with exponential backoff.

        Args:
            func: The async function to retry
            *args: Arguments to pass to the function
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Factor to multiply delay by after each retry

        Returns:
            The result of the function call

        Raises:
            The last exception encountered after all retries are exhausted
        """
        last_exception = None
        delay = initial_delay

        for attempt in range(max_retries):
            try:
                return await func(*args)

            except Exception as e:
                last_exception = e
                if attempt == max_retries - 1:  # Last attempt
                    log.error(f"Final retry attempt failed: {str(e)}")
                    raise

                # Log the error and retry
                log.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}. "
                    f"Retrying in {delay} seconds..."
                )

                # Wait before next retry
                await asyncio.sleep(delay)

                # Increase delay for next retry, but don't exceed max_delay
                delay = min(delay * backoff_factor, max_delay)

        # This should never be reached due to the raise in the loop
        raise last_exception if last_exception else RuntimeError("Retry loop exited unexpectedly")

    async def _sync_project_changelog(self, session: AsyncSession, issue_ids: List[str]) -> None:
        """Sync issues changelog from Jira API to database"""
        try:
            if len(issue_ids) == 0:
                return

            # Fetch all changelog data with admin auth (single API call)
            changelog_response = await self.jira_issue_api_service.bulk_get_issue_changelog_with_admin_auth(issue_ids)

            # Process each changelog individually
            for issue_changelog in changelog_response.issue_changelogs:
                for changelog in issue_changelog.change_histories:
                    # Convert changelog to database format
                    changes = await self.jira_issue_history_service.convert_api_changelog_to_db_changelog(
                        issue_changelog.issue_id,
                        changelog
                    )

                    # Create and save the event if we have changes
                    if changes:
                        event = JiraIssueHistoryDBCreateDTO(
                            jira_issue_id=issue_changelog.issue_id,
                            jira_change_id=changelog.id,
                            author_id=changelog.author.id,
                            created_at=changelog.created,
                            changes=changes
                        )

                        # Lưu vào database - ensure we're passing the session
                        await self.jira_issue_history_repository.create(session, event)
        except Exception as e:
            log.error(f"Error syncing project changelog: {str(e)}")
            raise
