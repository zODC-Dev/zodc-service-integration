from typing import Any, Dict

from src.configs.logger import log
from src.domain.constants.nats_events import NATSPublishTopic, NATSSubscribeTopic
from src.domain.constants.refresh_tokens import TokenType
from src.domain.entities.nats_event import (
    JiraUserInfo,
    JiraUsersRequestEvent,
    JiraUsersResponseEvent,
    ProjectLinkEvent,
    ProjectUnlinkEvent,
    TokenEvent,
    UserEvent,
)
from src.domain.entities.project import ProjectCreate, ProjectUpdate
from src.domain.entities.refresh_token import RefreshTokenEntity
from src.domain.repositories.project_repository import IProjectRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.repositories.user_repository import IUserRepository
from src.domain.services.jira_service import IJiraService
from src.domain.services.nats_service import INATSService
from src.domain.services.redis_service import IRedisService


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
            elif event_type.startswith("auth"):
                await self.nats_service.subscribe(
                    subject=event_type.value,
                    callback=self.handle_token_event
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

    async def handle_token_event(self, subject: str, message: Dict[str, Any]) -> None:
        """Handle token events and clear related caches"""
        log.info(f"Handling token event: {subject} for user {message['user_id']}")

        # Parse the event
        event = TokenEvent.model_validate(message)

        # Cache access token
        if event.token_type == TokenType.MICROSOFT:
            await self.redis_service.cache_microsoft_token(
                user_id=event.user_id,
                access_token=event.access_token,
                expiry=event.expires_in
            )
        else:
            await self.redis_service.cache_jira_token(
                user_id=event.user_id,
                access_token=event.access_token,
                expiry=event.expires_in
            )

        # Store refresh token
        await self.refresh_token_repository.create_refresh_token(
            RefreshTokenEntity(
                token=event.refresh_token,
                user_id=event.user_id,
                token_type=event.token_type,
                expires_at=event.expires_at
            )
        )

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
                # Update project to set is_linked = False
                await self.project_repository.update_project(
                    project.id,
                    ProjectUpdate(is_linked=False)
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
