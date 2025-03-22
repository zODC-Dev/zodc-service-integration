import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional, TypeVar

from src.app.dtos.jira.jira_project_sync import (
    JiraProjectSyncRequestDTO,
    JiraProjectSyncResponseDTO,
    JiraProjectSyncSummaryDTO,
)
from src.configs.logger import log
from src.domain.constants.jira import JiraIssueType
from src.domain.constants.nats_events import NATSPublishTopic
from src.domain.constants.sync import EntityType, OperationType, SourceType
from src.domain.models.jira_issue import JiraIssueModel
from src.domain.models.jira_project import JiraProjectCreateDTO, JiraProjectModel, JiraProjectUpdateDTO
from src.domain.models.jira_sprint import JiraSprintCreateDTO, JiraSprintModel, JiraSprintUpdateDTO
from src.domain.models.jira_user import JiraUserCreateDTO, JiraUserModel, JiraUserUpdateDTO
from src.domain.models.sync_log import SyncLogCreateDTO
from src.domain.repositories.sync_log_repository import ISyncLogRepository
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_project_database_service import IJiraProjectDatabaseService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService
from src.domain.unit_of_works.jira_sync_session import IJiraSyncSession

T = TypeVar('T')


class JiraProjectApplicationService:
    def __init__(
        self,
        jira_project_api_service: IJiraProjectAPIService,
        jira_project_db_service: IJiraProjectDatabaseService,
        jira_issue_db_service: IJiraIssueDatabaseService,
        jira_sprint_db_service: IJiraSprintDatabaseService,
        sync_session: IJiraSyncSession,
        sync_log_repository: ISyncLogRepository
    ):
        self.jira_project_api_service = jira_project_api_service
        self.jira_project_db_service = jira_project_db_service
        self.jira_issue_db_service = jira_issue_db_service
        self.jira_sprint_db_service = jira_sprint_db_service
        self.sync_session = sync_session
        self.sync_log_repository = sync_log_repository

    async def get_project_issues(
        self,
        user_id: int,
        project_key: str,
        sprint_id: Optional[str] = None,
        is_backlog: Optional[bool] = None,
        issue_type: Optional[JiraIssueType] = None,
        search: Optional[str] = None,
        limit: int = 50
    ) -> List[JiraIssueModel]:
        # Thay vì gọi API service, gọi database service
        return await self.jira_issue_db_service.get_project_issues(
            user_id=user_id,
            project_key=project_key,
            sprint_id=sprint_id,
            is_backlog=is_backlog,
            issue_type=issue_type,
            search=search,
            limit=limit
        )

    async def get_accessible_projects(self, user_id: int) -> List[JiraProjectModel]:
        """Get projects from database, if not found fetch from API and save"""
        # First try to get from database
        projects = await self.jira_project_db_service.get_all_projects()

        if not projects:
            # If no projects in database, fetch from API
            projects = await self.jira_project_api_service.get_accessible_projects(user_id)

            # Save to database
            for project in projects:
                create_dto = JiraProjectCreateDTO(
                    project_id=project.project_id,
                    key=project.key,
                    name=project.name,
                    jira_project_id=project.jira_project_id,
                    avatar_url=project.avatar_url,
                    description=project.description,
                )
                await self.jira_project_db_service.create_project(create_dto)

        return projects

    async def get_project_sprints(
        self,
        project_key: str,
    ) -> List[JiraSprintModel]:
        # Sprints are always fetched from API as they're dynamic
        sprints = await self.jira_sprint_db_service.get_project_sprints(
            project_key=project_key
        )
        log.info(f"Found {len(sprints)} sprints for project {project_key}")
        return sprints

    async def get_project_by_key(self, key: str) -> Optional[JiraProjectModel]:
        """Get project from database by key"""
        return await self.jira_project_db_service.get_project_by_key(key)

    async def update_project(
        self,
        project_id: int,
        project_data: JiraProjectUpdateDTO
    ) -> JiraProjectModel:
        """Update project in database"""
        return await self.jira_project_db_service.update_project(project_id, project_data)

    async def sync_project(self, request: JiraProjectSyncRequestDTO) -> JiraProjectSyncResponseDTO:
        try:
            log.info(f"Starting sync for project {request.project_key}")
            started_at = datetime.now(timezone.utc)
            async with self.sync_session as session:
                # Sync project details
                log.info("Syncing project details...")
                project = await self._sync_project_details(request.user_id, request.project_key, session)

                # Sync sprints
                log.info("Syncing project sprints...")
                sprint_id_mapping = await self._sync_project_sprints(request.user_id, request.project_key, session)
                log.info(f"Successfully synced {len(sprint_id_mapping)} sprints")

                # Sync issues
                log.info("Syncing project issues...")
                issues = await self._sync_project_issues(request.user_id, request.project_key, session)
                log.info(f"Successfully synced {len(issues)} issues")

                # Create sync log
                await self._create_sync_log(request.user_id, project)

                log.info(f"Successfully completed sync for project {request.project_key}")

                return JiraProjectSyncResponseDTO(
                    success=True,
                    project_key=request.project_key,
                    sync_summary=JiraProjectSyncSummaryDTO(
                        started_at=started_at.isoformat(),
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        total_sprints=len(sprint_id_mapping),
                        total_issues=len(issues)
                    )
                )

        except Exception as e:
            log.error(f"Error during project sync: {str(e)}")
            raise

    async def _publish_sync_result(
        self,
        project_key: str,
        success: bool,
        sync_summary: Optional[JiraProjectSyncSummaryDTO] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Publish sync result to NATS"""
        await self.nats_service.publish(
            NATSPublishTopic.JIRA_PROJECT_SYNC_RESULT.value,
            {
                "success": success,
                "project_key": project_key,
                "sync_summary": sync_summary.model_dump() if sync_summary else None,
                "error_message": error_message
            }
        )

    async def _sync_project_details(
        self,
        user_id: int,
        project_key: str,
        session: IJiraSyncSession
    ) -> JiraProjectModel:
        try:
            # Fetch from Jira API
            project_details = await self.jira_project_api_service.get_project_details(
                user_id=user_id,
                project_key=project_key
            )

            # Check if project exists
            existing_project = await session.project_repository.get_project_by_key(project_key)

            if existing_project:
                # Update existing project
                update_dto = JiraProjectUpdateDTO(
                    name=project_details.name,
                    avatar_url=project_details.avatar_url,
                    description=project_details.description
                )
                return await session.project_repository.update_project(
                    existing_project.id,
                    update_dto
                )
            else:
                # Create new project
                create_dto = JiraProjectCreateDTO(
                    jira_project_id=project_details.jira_project_id,
                    key=project_details.key,
                    name=project_details.name,
                    description=project_details.description,
                    avatar_url=project_details.avatar_url
                )
                return await session.project_repository.create_project(create_dto)

        except Exception as e:
            log.error(f"Error syncing project details: {str(e)}", exc_info=True)
            raise

    async def _sync_project_users(
        self,
        user_id: int,
        project_key: str,
        session: IJiraSyncSession
    ) -> List[JiraUserModel]:
        """Sync project users from Jira API to database"""
        try:
            # Fetch users from Jira API
            jira_users = await self.jira_project_api_service.get_project_users(
                user_id=user_id,
                project_key=project_key
            )

            synced_users = []
            for jira_user in jira_users:
                try:
                    # Check if user exists by jira_account_id
                    existing_user = await session.user_repository.get_user_by_account_id(
                        jira_user.jira_account_id
                    )
                    log.info(f"Existing user: {existing_user} {jira_user.jira_account_id}")

                    if existing_user:
                        # Update existing user if needed
                        update_dto = JiraUserUpdateDTO(
                            email=jira_user.email,
                            avatar_url=jira_user.avatar_url
                        )
                        await session.user_repository.update_user(update_dto)
                        synced_users.append(existing_user)
                    else:
                        # Create new user only if they don't exist
                        create_dto = JiraUserCreateDTO(
                            jira_account_id=jira_user.jira_account_id,
                            email=jira_user.email,
                            avatar_url=jira_user.avatar_url,
                            is_system_user=False
                        )
                        new_user = await session.user_repository.create_user(create_dto)
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
        user_id: int,
        project_key: str,
        session: IJiraSyncSession
    ) -> dict[int, int]:
        sprint_id_mapping = {}
        sprints = await self.jira_project_api_service.get_project_sprints(user_id, project_key)

        for sprint in sprints:
            try:
                # Check if sprint exists by jira_sprint_id
                existing_sprint = await session.sprint_repository.get_by_jira_sprint_id(sprint.jira_sprint_id)

                sprint_data = JiraSprintCreateDTO(
                    jira_sprint_id=sprint.jira_sprint_id,
                    name=sprint.name,
                    state=sprint.state,
                    start_date=sprint.start_date,
                    end_date=sprint.end_date,
                    complete_date=sprint.complete_date,
                    goal=sprint.goal,
                    project_key=project_key
                )

                if existing_sprint:
                    # Update if exists
                    updated_sprint = await session.sprint_repository.update_sprint(
                        existing_sprint.id,
                        JiraSprintUpdateDTO(**sprint_data.model_dump())
                    )
                    if updated_sprint:
                        sprint_id_mapping[sprint.jira_sprint_id] = updated_sprint.id
                else:
                    # Create new if not exists
                    new_sprint = await session.sprint_repository.create_sprint(sprint_data)
                    sprint_id_mapping[sprint.jira_sprint_id] = new_sprint.id

                log.info(f"Successfully synced sprint {sprint.name} for project {project_key}")

            except Exception as e:
                log.error(f"Error syncing sprint {sprint.jira_sprint_id}: {str(e)}")
                continue

        return sprint_id_mapping

    async def _sync_project_issues(
        self,
        user_id: int,
        project_key: str,
        session: IJiraSyncSession
    ) -> List[JiraIssueModel]:
        """Sync all project issues from Jira API to database"""
        try:
            jira_issues = await self.jira_project_api_service.get_project_issues(
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
                    existing_issue = await session.issue_repository.get_by_jira_issue_id(
                        jira_issue.jira_issue_id
                    )

                    if existing_issue:
                        if jira_issue.updated_at > existing_issue.last_synced_at:
                            # Update existing issue with new data
                            updated_issue = await session.issue_repository.update(jira_issue)
                            synced_issues.append(updated_issue)
                    else:
                        # Create new issue
                        new_issue = await session.issue_repository.create(jira_issue)
                        synced_issues.append(new_issue)

                except Exception as e:
                    log.error(f"Error syncing issue {jira_issue.key}: {str(e)}")
                    await session.abort()
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

    async def _create_sync_log(self, user_id: int, project: JiraProjectModel) -> None:
        """Create sync log entry for project sync"""
        try:
            await self.sync_log_repository.create_sync_log(
                SyncLogCreateDTO(
                    entity_type=EntityType.PROJECT,
                    entity_id=project.key,
                    operation=OperationType.SYNC,
                    request_payload={},  # No specific payload for sync
                    response_status=200,  # Success status
                    response_body={
                        "project_key": project.key,
                        "project_name": project.name,
                        "sync_time": datetime.now(timezone.utc).isoformat()
                    },
                    source=SourceType.NATS,
                    sender=user_id,
                    error_message=None
                )
            )
        except Exception as e:
            log.error(f"Error creating sync log for project {project.key}: {str(e)}")
            # Don't raise the error as this is not critical for sync process
