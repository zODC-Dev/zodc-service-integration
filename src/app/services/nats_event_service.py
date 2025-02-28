from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from src.configs.logger import log
from src.domain.constants.nats_events import NATSPublishTopic, NATSSubscribeTopic
from src.domain.constants.refresh_tokens import TokenType
from src.domain.constants.jira import JiraActionType
from src.domain.entities.nats_event import (
    JiraIssueSyncPayload,
    JiraIssueSyncResultPayload,
    JiraLoginEvent,
    JiraUserInfo,
    JiraUsersRequestEvent,
    JiraUsersResponseEvent,
    MicrosoftLoginEvent,
    ProjectLinkEvent,
    ProjectUnlinkEvent,
    UserEvent,
)
from src.domain.entities.project import ProjectCreate, ProjectUpdate
from src.domain.entities.refresh_token import RefreshTokenEntity
from src.domain.entities.user import UserCreate, UserUpdate
from src.domain.repositories.project_repository import IProjectRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.repositories.user_repository import IUserRepository
from src.domain.services.jira_service import IJiraService
from src.domain.services.nats_service import INATSService
from src.domain.services.redis_service import IRedisService
from src.utils.jwt_utils import get_jwt_expiry


class NATSEventService:
    def __init__(
        self,
        nats_service: INATSService,
        redis_service: IRedisService,
        user_repository: IUserRepository,
        refresh_token_repository: IRefreshTokenRepository,
        project_repository: IProjectRepository,
        jira_service: IJiraService
    ):
        self.nats_service = nats_service
        self.redis_service = redis_service
        self.user_repository = user_repository
        self.refresh_token_repository = refresh_token_repository
        self.project_repository = project_repository
        self.jira_service = jira_service

    async def start_nats_subscribers(self) -> None:
        """Start NATS subscribers"""
        for event_type in NATSSubscribeTopic:
            if event_type.startswith("user"):
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_user_event
                )
            elif event_type == NATSSubscribeTopic.USER_MICROSOFT_LOGIN:
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_microsoft_login_event
                )
            elif event_type == NATSSubscribeTopic.USER_JIRA_LOGIN:
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_jira_login_event
                )
            elif event_type == NATSSubscribeTopic.PROJECT_LINKED:
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_project_link_event
                )
            elif event_type == NATSSubscribeTopic.PROJECT_UNLINKED:
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_project_unlink_event
                )
            elif event_type == NATSSubscribeTopic.PROJECT_USERS_REQUEST:
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_project_users_request
                )
            elif event_type == NATSSubscribeTopic.JIRA_ISSUES_SYNC:
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_jira_issues_sync
                )

    async def handle_user_event(self, subject: str, message: Dict[str, Any]) -> None:
        # Parse the event
        event = UserEvent.model_validate(message)

        """Handle user events and clear related caches"""
        log.info(f"Handling user event: {event.event_type} for user {event.user_id}")

        # Clear Jira token cache for the user
        await self.redis_service.delete(f"jira_token:{event.user_id}")

        # Clear Microsoft token cache for the user
        await self.redis_service.delete(f"microsoft_token:{event.user_id}")

        log.info(f"Cleared cache for user {event.user_id}")

    async def handle_project_link_event(self, subject: str, message: Dict[str, Any]) -> None:
        """Handle project link events"""
        try:
            # Parse the event
            event = ProjectLinkEvent.model_validate(message)

            # Create new project record
            project = ProjectCreate(
                project_id=event.project_id,
                jira_project_id=event.jira_project_id,
                name=event.name,
                key=event.key,
                avatar_url=event.avatar_url,
            )

            # Save to database
            await self.project_repository.create_project(project)

            log.info(f"Project {event.name} ({event.key}) linked successfully")

        except Exception as e:
            log.error(f"Error handling project link event: {str(e)}")

    async def handle_project_unlink_event(self, subject: str, message: Dict[str, Any]) -> None:
        """Handle project unlink events"""
        try:
            # Parse the event
            event = ProjectUnlinkEvent.model_validate(message)

            # Find the project by jira_project_id
            project = await self.project_repository.get_by_jira_project_id(event.jira_project_id)

            if project and project.id:
                # Update project to set is_jira_linked = False
                await self.project_repository.update_project(
                    project.id,
                    ProjectUpdate(is_jira_linked=False)
                )

                log.info(f"Project {project.name} unlinked successfully")
            else:
                log.warning(f"Project with Jira ID {event.jira_project_id} not found for unlinking")

        except Exception as e:
            log.error(f"Error handling project unlink event: {str(e)}")

    async def handle_project_users_request(self, subject: str, message: Dict[str, Any]) -> None:
        """Handle project users request events"""
        try:
            # Parse the event
            event = JiraUsersRequestEvent.model_validate(message)

            # Get project users from Jira
            users = await self.jira_service.get_project_users(
                user_id=event.admin_user_id,
                project_key=event.key
            )

            # Transform to response format
            jira_users = [
                JiraUserInfo(
                    jira_account_id=user.account_id,
                    email=user.email_address,
                    name=user.display_name
                )
                for user in users
            ]

            # Prepare response
            response = JiraUsersResponseEvent(
                project_id=event.project_id,
                jira_project_id=event.jira_project_id,
                users=jira_users
            )

            # Publish response
            await self.nats_service.publish(
                NATSPublishTopic.PROJECT_USERS_RESPONSE.value,
                response.model_dump()
            )

        except Exception as e:
            log.error(f"Error handling project users request: {str(e)}")

    async def handle_microsoft_login_event(self, subject: str, message: Dict[str, Any]) -> None:
        """Handle Microsoft login event - create user and store tokens"""
        try:
            # Parse the event data
            event = MicrosoftLoginEvent.model_validate(message)

            # Check if user exists
            user = await self.user_repository.get_user_by_email(event.email)

            if not user:
                # Create new user
                new_user = UserCreate(
                    email=event.email,
                    user_id=event.user_id,
                )
                await self.user_repository.create_user(new_user)
                log.info(f"Created new user from Microsoft login for user {event.user_id}")

            # Store refresh token
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=event.expires_in * 2)
            refresh_token = RefreshTokenEntity(
                token=event.refresh_token,
                user_id=event.user_id,
                token_type=TokenType.MICROSOFT,
                expires_at=expires_at
            )
            await self.refresh_token_repository.create_refresh_token(refresh_token)

            # Cache access token
            await self.redis_service.cache_microsoft_token(
                user_id=event.user_id,
                access_token=event.access_token,
                expiry=event.expires_in
            )

            log.info(f"Successfully processed Microsoft login for user {event.user_id}")

        except Exception as e:
            log.error(f"Error handling Microsoft login event: {str(e)}")

    async def handle_jira_login_event(self, subject: str, message: Dict[str, Any]) -> None:
        """Handle Jira login event - create/update user and store tokens"""
        try:
            # Parse the event data
            event = JiraLoginEvent.model_validate(message)

            # Check if user exists
            user = await self.user_repository.get_user_by_email(event.email)

            if user:
                # Update Jira info if user exists
                user_update = UserUpdate(
                    email=event.email,
                    jira_account_id=event.jira_account_id,
                )
                await self.user_repository.update_user(user_update)
                log.info(f"Updated Jira link for existing user {user.id}")
            else:
                # Create new user with Jira info
                new_user = UserCreate(
                    email=event.email,
                    user_id=event.user_id,
                    jira_account_id=event.jira_account_id,
                )
                await self.user_repository.create_user(new_user)
                log.info(f"Created new user with Jira link for user {event.user_id}")

            # Store refresh token
            expires_at = get_jwt_expiry(event.refresh_token) or datetime.now(
                timezone.utc) + timedelta(seconds=event.expires_in * 2)
            refresh_token = RefreshTokenEntity(
                token=event.refresh_token,
                user_id=event.user_id,
                token_type=TokenType.JIRA,
                expires_at=expires_at
            )
            await self.refresh_token_repository.create_refresh_token(refresh_token)

            # Cache access token
            await self.redis_service.cache_jira_token(
                user_id=event.user_id,
                access_token=event.access_token,
                expiry=event.expires_in
            )

            log.info(f"Successfully processed Jira login for user {event.user_id}")

        except Exception as e:
            log.error(f"Error handling Jira login event: {str(e)}")

    async def handle_jira_issues_sync(self, subject: str, message: List[Dict[str, Any]]) -> None:
        """Handle Jira issues sync events"""
        results = []

        try:
            # Parse each issue in the batch
            issues = [JiraIssueSyncPayload.model_validate(item) for item in message]

            # Process each issue
            for issue in issues:
                result = JiraIssueSyncResultPayload(
                    success=False,
                    action_type=issue.action_type,
                    issue_id=issue.issue_id
                )

                try:
                    if issue.action_type == JiraActionType.CREATE:
                        # Validate required fields for creation
                        if not issue.project_key or not issue.summary or not issue.issue_type:
                            error_msg = "Missing required fields for issue creation"
                            log.error(f"{error_msg}: {issue}")
                            result.error_message = error_msg
                            results.append(result.model_dump())
                            continue

                        # Create new issue
                        from src.domain.entities.jira import JiraIssueCreate
                        create_payload = JiraIssueCreate(
                            project_key=issue.project_key,
                            summary=issue.summary,
                            description=issue.description,
                            issue_type=issue.issue_type,
                            assignee=issue.assignee,
                            estimate_points=issue.estimate_points
                        )

                        created_issue = await self.jira_service.create_issue(
                            user_id=issue.user_id,
                            issue=create_payload
                        )

                        log.info(f"Successfully created issue {created_issue.issue_id}")
                        result.success = True
                        result.issue_id = created_issue.issue_id

                    elif issue.action_type == JiraActionType.UPDATE:
                        # Validate required fields for update
                        if not issue.issue_id:
                            error_msg = "Missing issue_id for issue update"
                            log.error(f"{error_msg}: {issue}")
                            result.error_message = error_msg
                            results.append(result.model_dump())
                            continue

                        # Update existing issue
                        from src.domain.entities.jira import JiraIssueUpdate
                        update_payload = JiraIssueUpdate(
                            summary=issue.summary,
                            description=issue.description,
                            status=issue.status,
                            assignee=issue.assignee,
                            estimate_points=issue.estimate_points,
                            actual_points=issue.actual_points
                        )

                        await self.jira_service.update_issue(
                            user_id=issue.user_id,
                            issue_id=issue.issue_id,
                            update=update_payload
                        )

                        log.info(f"Successfully updated issue {issue.issue_id}")
                        result.success = True

                except Exception as e:
                    error_msg = str(e)
                    log.error(f"Error processing issue {issue.issue_id if issue.issue_id else 'new'}: {error_msg}")
                    result.error_message = error_msg

                results.append(result.model_dump())

            log.info(f"Completed processing {len(issues)} issues")

            # Publish results
            await self.nats_service.publish(
                NATSPublishTopic.JIRA_ISSUES_SYNC_RESULT.value,
                results
            )

        except Exception as e:
            log.error(f"Error handling Jira issues sync event: {str(e)}")

            # Publish error result if we couldn't process the batch
            error_result = JiraIssueSyncResultPayload(
                success=False,
                action_type=JiraActionType.CREATE,  # Default
                error_message=f"Batch processing error: {str(e)}"
            )
            await self.nats_service.publish(
                NATSPublishTopic.JIRA_ISSUES_SYNC_RESULT.value,
                [error_result.model_dump()]
            )
