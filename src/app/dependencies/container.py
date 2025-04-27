from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from redis.asyncio import Redis

from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.app.services.jira_issue_history_service import JiraIssueHistoryApplicationService
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.app.services.jira_project_service import JiraProjectApplicationService
from src.app.services.media_service import MediaApplicationService
from src.app.services.nats_application_service import NATSApplicationService
from src.app.services.nats_event_service import NATSEventService
from src.app.services.nats_handlers.gantt_chart_handler import GanttChartRequestHandler
from src.app.services.nats_handlers.jira_issue_link_handler import JiraIssueLinkRequestHandler
from src.app.services.nats_handlers.jira_issue_reassign_handler import JiraIssueReassignRequestHandler
from src.app.services.nats_handlers.jira_issue_sync_handler import JiraIssueSyncRequestHandler
from src.app.services.nats_handlers.jira_login_message_handler import JiraLoginMessageHandler
from src.app.services.nats_handlers.jira_project_sync_handler import JiraProjectSyncRequestHandler
from src.app.services.nats_handlers.microsoft_login_message_handler import MicrosoftLoginMessageHandler
from src.app.services.nats_handlers.node_status_sync_handler import NodeStatusSyncHandler
from src.app.services.nats_handlers.user_message_handler import UserMessageHandler
from src.app.services.nats_handlers.workflow_edit_handler import WorkflowEditRequestHandler
from src.app.services.nats_handlers.workflow_sync_handler import WorkflowSyncRequestHandler
from src.app.services.system_config_service import SystemConfigApplicationService
from src.configs.database import get_db, session_maker
from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.nats_events import NATSSubscribeTopic
from src.domain.services.jira_issue_api_service import IJiraIssueAPIService
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_user_api_service import IJiraUserAPIService
from src.domain.services.nats_message_handler import INATSMessageHandler, INATSRequestHandler
from src.infrastructure.repositories.sqlalchemy_jira_issue_history_repository import (
    SQLAlchemyJiraIssueHistoryRepository,
)
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyJiraProjectRepository
from src.infrastructure.repositories.sqlalchemy_jira_sprint_repository import SQLAlchemyJiraSprintRepository
from src.infrastructure.repositories.sqlalchemy_jira_user_repository import SQLAlchemyJiraUserRepository
from src.infrastructure.repositories.sqlalchemy_media_repository import SQLAlchemyMediaRepository
from src.infrastructure.repositories.sqlalchemy_refresh_token_repository import SQLAlchemyRefreshTokenRepository
from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository
from src.infrastructure.repositories.sqlalchemy_system_config_repository import SQLAlchemySystemConfigRepository
from src.infrastructure.repositories.sqlalchemy_workflow_mapping_repository import SQLAlchemyWorkflowMappingRepository
from src.infrastructure.services.gantt_chart_calculator_service import GanttChartCalculatorService
from src.infrastructure.services.jira_issue_api_service import JiraIssueAPIService
from src.infrastructure.services.jira_issue_database_service import JiraIssueDatabaseService
from src.infrastructure.services.jira_issue_history_database_service import JiraIssueHistoryDatabaseService
from src.infrastructure.services.jira_project_api_service import JiraProjectAPIService
from src.infrastructure.services.jira_project_database_service import JiraProjectDatabaseService
from src.infrastructure.services.jira_service import JiraAPIClient
from src.infrastructure.services.jira_sprint_api_service import JiraSprintAPIService
from src.infrastructure.services.jira_sprint_database_service import JiraSprintDatabaseService
from src.infrastructure.services.jira_user_api_service import JiraUserAPIService
from src.infrastructure.services.jira_user_database_service import JiraUserDatabaseService
from src.infrastructure.services.nats_service import NATSService
from src.infrastructure.services.nats_workflow_service_client import NATSWorkflowServiceClient
from src.infrastructure.services.redis_service import RedisService
from src.infrastructure.services.token_refresh_service import TokenRefreshService
from src.infrastructure.services.token_scheduler_service import TokenSchedulerService
from src.infrastructure.unit_of_works.sqlalchemy_jira_sync_session import SQLAlchemyJiraSyncSession


class DependencyContainer:
    """Centralized container for all application dependencies"""

    _instance: Optional['DependencyContainer'] = None

    # Database session
    db = None

    # Services
    redis_client: Optional[Redis] = None
    redis_service: Optional[RedisService] = None
    nats_service: Optional[NATSService] = None
    scheduler: Optional[AsyncIOScheduler] = None

    # Repositories
    jira_user_repository: Optional[SQLAlchemyJiraUserRepository] = None
    refresh_token_repository: Optional[SQLAlchemyRefreshTokenRepository] = None
    project_repository: Optional[SQLAlchemyJiraProjectRepository] = None
    sync_log_repository: Optional[SQLAlchemySyncLogRepository] = None
    jira_issue_repository: Optional[SQLAlchemyJiraIssueRepository] = None
    jira_sprint_repository: Optional[SQLAlchemyJiraSprintRepository] = None
    issue_history_repository: Optional[SQLAlchemyJiraIssueHistoryRepository] = None
    workflow_mapping_repository: Optional[SQLAlchemyWorkflowMappingRepository] = None
    media_repository: Optional[SQLAlchemyMediaRepository] = None
    system_config_repository: Optional[SQLAlchemySystemConfigRepository] = None

    # Infrastructure services
    token_refresh_service: Optional[TokenRefreshService] = None
    token_scheduler_service: Optional[TokenSchedulerService] = None
    jira_issue_database_service: Optional[JiraIssueDatabaseService] = None
    jira_api_client: Optional[JiraAPIClient] = None
    jira_api_admin_client: Optional[JiraAPIClient] = None
    jira_issue_api_service: Optional[IJiraIssueAPIService] = None
    jira_sprint_api_service: Optional[IJiraSprintAPIService] = None
    jira_user_api_service: Optional[IJiraUserAPIService] = None
    sync_session: Optional[SQLAlchemyJiraSyncSession] = None
    jira_project_api_service: Optional[IJiraProjectAPIService] = None
    jira_project_database_service: Optional[JiraProjectDatabaseService] = None
    jira_sprint_database_service: Optional[JiraSprintDatabaseService] = None
    issue_history_db_service: Optional[JiraIssueHistoryDatabaseService] = None
    jira_user_db_service: Optional[JiraUserDatabaseService] = None
    gantt_calculator_service: Optional[GanttChartCalculatorService] = None
    workflow_service_client: Optional[NATSWorkflowServiceClient] = None

    # Application services
    jira_issue_application_service: Optional[JiraIssueApplicationService] = None
    jira_project_application_service: Optional[JiraProjectApplicationService] = None
    issue_history_sync_service: Optional[JiraIssueHistoryApplicationService] = None
    gantt_chart_service: Optional[GanttChartApplicationService] = None
    nats_event_service: Optional[NATSEventService] = None
    media_application_service: Optional[MediaApplicationService] = None
    system_config_application_service: Optional[SystemConfigApplicationService] = None
    nats_application_service: Optional[NATSApplicationService] = None
    # Handlers
    message_handlers: Dict[str, INATSMessageHandler] = {}
    request_handlers: Dict[str, INATSRequestHandler] = {}

    @classmethod
    def get_instance(cls) -> 'DependencyContainer':
        if cls._instance is None:
            cls._instance = DependencyContainer()
        return cls._instance

    @classmethod
    async def initialize(cls) -> None:
        """Initialize all dependencies"""
        instance = cls.get_instance()

        # Initialize database session
        db_generator = get_db()
        instance.db = await anext(db_generator)

        # Initialize Redis
        instance.redis_client = Redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            encoding="utf-8",
            decode_responses=True
        )
        instance.redis_service = RedisService(instance.redis_client)

        # Initialize NATS service
        instance.nats_service = NATSService()
        await instance.nats_service.connect()

        # Initialize repositories
        instance.jira_user_repository = SQLAlchemyJiraUserRepository(instance.db)
        instance.refresh_token_repository = SQLAlchemyRefreshTokenRepository(instance.db)
        instance.project_repository = SQLAlchemyJiraProjectRepository(instance.db)
        instance.sync_log_repository = SQLAlchemySyncLogRepository(instance.db)
        instance.jira_issue_repository = SQLAlchemyJiraIssueRepository(instance.db)
        instance.jira_sprint_repository = SQLAlchemyJiraSprintRepository(instance.db)
        instance.issue_history_repository = SQLAlchemyJiraIssueHistoryRepository(instance.db)
        instance.workflow_mapping_repository = SQLAlchemyWorkflowMappingRepository(instance.db)
        instance.media_repository = SQLAlchemyMediaRepository(instance.db)
        instance.system_config_repository = SQLAlchemySystemConfigRepository(instance.db)

        # Initialize token services
        instance.token_refresh_service = TokenRefreshService(
            instance.redis_service,
            instance.jira_user_repository,
            instance.refresh_token_repository
        )
        instance.token_scheduler_service = TokenSchedulerService(
            instance.token_refresh_service,
            instance.refresh_token_repository
        )

        # Initialize Jira services
        instance.jira_issue_database_service = JiraIssueDatabaseService(
            instance.jira_issue_repository
        )

        instance.jira_api_client = JiraAPIClient(
            redis_service=instance.redis_service,
            token_scheduler_service=instance.token_scheduler_service,
        )

        instance.jira_api_admin_client = JiraAPIClient(
            redis_service=instance.redis_service,
            token_scheduler_service=instance.token_scheduler_service,
            use_admin_auth=True
        )

        instance.jira_issue_api_service = JiraIssueAPIService(
            client=instance.jira_api_client,
            user_repository=instance.jira_user_repository,
            admin_client=instance.jira_api_admin_client
        )

        instance.jira_sprint_api_service = JiraSprintAPIService(
            client=instance.jira_api_client,
            admin_client=instance.jira_api_admin_client
        )

        instance.jira_user_api_service = JiraUserAPIService(
            client=instance.jira_api_client,
            admin_client=instance.jira_api_admin_client
        )

        instance.jira_issue_application_service = JiraIssueApplicationService(
            instance.jira_issue_database_service,
            instance.jira_issue_api_service,
            instance.jira_issue_repository,
            instance.project_repository,
            instance.nats_service,
            instance.sync_log_repository
        )

        instance.sync_session = SQLAlchemyJiraSyncSession(session_maker)

        instance.jira_project_api_service = JiraProjectAPIService(
            instance.jira_api_client,
            instance.jira_user_repository
        )

        instance.jira_project_database_service = JiraProjectDatabaseService(
            instance.project_repository
        )

        instance.jira_sprint_database_service = JiraSprintDatabaseService(
            instance.jira_sprint_repository
        )

        instance.issue_history_db_service = JiraIssueHistoryDatabaseService(
            instance.issue_history_repository
        )

        instance.jira_user_db_service = JiraUserDatabaseService(
            instance.jira_user_repository
        )

        instance.issue_history_sync_service = JiraIssueHistoryApplicationService(
            instance.jira_issue_api_service,
            instance.issue_history_db_service,
            instance.jira_issue_database_service,
            instance.jira_user_db_service
        )

        instance.jira_project_application_service = JiraProjectApplicationService(
            jira_project_api_service=instance.jira_project_api_service,
            jira_project_db_service=instance.jira_project_database_service,
            jira_issue_db_service=instance.jira_issue_database_service,
            jira_sprint_db_service=instance.jira_sprint_database_service,
            sync_session=instance.sync_session,
            sync_log_repository=instance.sync_log_repository,
            jira_issue_api_service=instance.jira_issue_api_service,
            jira_issue_history_service=instance.issue_history_sync_service
        )

        instance.gantt_calculator_service = GanttChartCalculatorService()
        instance.workflow_service_client = NATSWorkflowServiceClient(instance.nats_service)

        instance.gantt_chart_service = GanttChartApplicationService(
            instance.jira_issue_repository,
            instance.jira_sprint_repository,
            instance.workflow_mapping_repository,
            instance.gantt_calculator_service,
            instance.workflow_service_client
        )

        instance.nats_application_service = NATSApplicationService(instance.nats_service)

        # Initialize NATS handlers
        instance.message_handlers = {
            NATSSubscribeTopic.USER_EVENT.value: UserMessageHandler(instance.redis_service),
            NATSSubscribeTopic.MICROSOFT_LOGIN.value: MicrosoftLoginMessageHandler(
                redis_service=instance.redis_service,
                user_repository=instance.jira_user_repository,
                refresh_token_repository=instance.refresh_token_repository
            ),
            NATSSubscribeTopic.JIRA_LOGIN.value: JiraLoginMessageHandler(
                redis_service=instance.redis_service,
                user_repository=instance.jira_user_repository,
                refresh_token_repository=instance.refresh_token_repository
            ),
        }

        instance.request_handlers = {
            NATSSubscribeTopic.JIRA_ISSUES_SYNC.value: JiraIssueSyncRequestHandler(
                instance.jira_issue_application_service
            ),
            NATSSubscribeTopic.JIRA_PROJECT_SYNC.value: JiraProjectSyncRequestHandler(
                instance.jira_project_application_service,
                instance.sync_log_repository
            ),
            NATSSubscribeTopic.JIRA_ISSUE_LINK.value: JiraIssueLinkRequestHandler(
                instance.jira_issue_application_service
            ),
            NATSSubscribeTopic.WORKFLOW_SYNC.value: WorkflowSyncRequestHandler(
                instance.jira_issue_application_service,
                instance.jira_user_repository,
                instance.jira_sprint_repository,
                instance.workflow_mapping_repository,
                instance.redis_service,
                instance.jira_issue_repository
            ),
            NATSSubscribeTopic.GANTT_CHART_CALCULATION.value: GanttChartRequestHandler(
                instance.gantt_chart_service
            ),
            NATSSubscribeTopic.NODE_STATUS_SYNC.value: NodeStatusSyncHandler(
                instance.jira_issue_api_service
            ),
            NATSSubscribeTopic.WORKFLOW_EDIT.value: WorkflowEditRequestHandler(
                instance.jira_issue_application_service,
                instance.jira_user_repository,
                instance.jira_sprint_repository,
                instance.workflow_mapping_repository,
                instance.redis_service,
                instance.jira_issue_repository
            ),
            NATSSubscribeTopic.JIRA_ISSUE_REASSIGN.value: JiraIssueReassignRequestHandler(
                instance.jira_issue_application_service,
                instance.jira_user_repository
            )
        }

        # Initialize NATS Event Service
        instance.nats_event_service = NATSEventService(
            nats_service=instance.nats_service,
            message_handlers=instance.message_handlers,
            request_handlers=instance.request_handlers
        )

        # Initialize scheduler
        instance.scheduler = AsyncIOScheduler()

    @classmethod
    async def cleanup(cls) -> None:
        """Clean up all resources"""
        instance = cls.get_instance()

        # Shutdown scheduler
        if instance.scheduler:
            instance.scheduler.shutdown()

        # Close Redis connection
        if instance.redis_client:
            await instance.redis_client.close()

        # Close NATS connection
        if instance.nats_service:
            await instance.nats_service.disconnect()

        # Close database connection
        if instance.db:
            await instance.db.close()

        # Reset instance
        cls._instance = None

    @classmethod
    async def get_db_for_job(cls):
        """Get a new DB session for background jobs"""
        db_generator = get_db()
        db = await anext(db_generator)
        try:
            return db
        finally:
            await db.close()

    @classmethod
    async def create_webhook_handlers(cls, session) -> Tuple[List[Callable[[], Awaitable[None]]], Dict[str, Any]]:
        """Create webhook handlers with optional session"""
        from redis.asyncio import Redis

        from src.app.services.jira_issue_history_service import JiraIssueHistoryApplicationService
        from src.app.services.jira_webhook_handlers.issue_create_webhook_handler import IssueCreateWebhookHandler
        from src.app.services.jira_webhook_handlers.issue_delete_webhook_handler import IssueDeleteWebhookHandler
        from src.app.services.jira_webhook_handlers.issue_update_webhook_handler import IssueUpdateWebhookHandler
        from src.app.services.jira_webhook_handlers.sprint_close_webhook_handler import SprintCloseWebhookHandler
        from src.app.services.jira_webhook_handlers.sprint_create_webhook_handler import SprintCreateWebhookHandler
        from src.app.services.jira_webhook_handlers.sprint_delete_webhook_handler import SprintDeleteWebhookHandler
        from src.app.services.jira_webhook_handlers.sprint_start_webhook_handler import SprintStartWebhookHandler
        from src.app.services.jira_webhook_handlers.sprint_update_webhook_handler import SprintUpdateWebhookHandler
        from src.app.services.jira_webhook_handlers.user_create_webhook_handler import UserCreateWebhookHandler
        from src.app.services.jira_webhook_handlers.user_delete_webhook_handler import UserDeleteWebhookHandler
        from src.app.services.jira_webhook_handlers.user_update_webhook_handler import UserUpdateWebhookHandler
        from src.configs.settings import settings
        from src.infrastructure.repositories.sqlalchemy_jira_issue_history_repository import (
            SQLAlchemyJiraIssueHistoryRepository,
        )
        from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
        from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyJiraProjectRepository
        from src.infrastructure.repositories.sqlalchemy_jira_sprint_repository import SQLAlchemyJiraSprintRepository
        from src.infrastructure.repositories.sqlalchemy_jira_user_repository import SQLAlchemyJiraUserRepository
        from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository
        from src.infrastructure.services.jira_issue_database_service import JiraIssueDatabaseService
        from src.infrastructure.services.jira_issue_history_database_service import JiraIssueHistoryDatabaseService
        from src.infrastructure.services.jira_sprint_database_service import JiraSprintDatabaseService
        from src.infrastructure.services.jira_user_database_service import JiraUserDatabaseService
        from src.infrastructure.services.redis_service import RedisService

        # Tạo các repositories cần thiết
        issue_repo = SQLAlchemyJiraIssueRepository(session)
        sync_log_repo = SQLAlchemySyncLogRepository(session)
        project_repo = SQLAlchemyJiraProjectRepository(session)
        sprint_repo = SQLAlchemyJiraSprintRepository(session)
        user_repo = SQLAlchemyJiraUserRepository(session)
        issue_history_repo = SQLAlchemyJiraIssueHistoryRepository(session)

        # Lấy services từ container chính
        container = cls.get_instance()

        # Tạo Redis service mới cho session này
        redis_client = Redis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            encoding="utf-8",
            decode_responses=True
        )
        redis_service = RedisService(redis_client)

        # Sử dụng các services từ container chính
        jira_issue_api_service = container.jira_issue_api_service
        jira_sprint_api_service = container.jira_sprint_api_service
        jira_user_api_service = container.jira_user_api_service
        # Tạo các services cần thiết
        jira_issue_db_service = JiraIssueDatabaseService(issue_repo)
        jira_user_db_service = JiraUserDatabaseService(user_repo)
        sprint_database_service = JiraSprintDatabaseService(sprint_repo)
        issue_history_db_service = JiraIssueHistoryDatabaseService(issue_history_repo)

        issue_history_sync_service = JiraIssueHistoryApplicationService(
            jira_issue_api_service,
            issue_history_db_service,
            jira_issue_db_service,
            jira_user_db_service
        )

        # Tạo handlers
        handlers = [
            # Issue handlers
            IssueCreateWebhookHandler(issue_repo, sync_log_repo, jira_issue_api_service, project_repo, redis_service),
            IssueUpdateWebhookHandler(
                jira_issue_repository=issue_repo,
                sync_log_repository=sync_log_repo,
                jira_issue_api_service=jira_issue_api_service,
                issue_history_sync_service=issue_history_sync_service,
                nats_application_service=container.nats_application_service,
                jira_sprint_repository=sprint_repo
            ),
            IssueDeleteWebhookHandler(issue_repo, sync_log_repo),

            # Sprint handlers
            SprintCreateWebhookHandler(sprint_database_service, sync_log_repo, jira_sprint_api_service),
            SprintUpdateWebhookHandler(sprint_database_service, sync_log_repo, jira_sprint_api_service),
            SprintStartWebhookHandler(sprint_database_service, sync_log_repo, jira_sprint_api_service),
            SprintCloseWebhookHandler(sprint_database_service, sync_log_repo, jira_sprint_api_service, issue_repo),
            SprintDeleteWebhookHandler(sprint_database_service, sync_log_repo, jira_sprint_api_service),

            # User handlers
            UserCreateWebhookHandler(jira_user_db_service, sync_log_repo, jira_user_api_service),
            UserUpdateWebhookHandler(jira_user_db_service, sync_log_repo, jira_user_api_service),
            UserDeleteWebhookHandler(jira_user_db_service, sync_log_repo)
        ]

        # Đóng gói vào một dictionary để trả về
        services_dict: Dict[str, Any] = {
            'jira_issue_api_service': jira_issue_api_service,
            'jira_sprint_api_service': jira_sprint_api_service,
            'sprint_database_service': sprint_database_service,
            'issue_history_sync_service': issue_history_sync_service,
            'issue_repo': issue_repo,
            'sync_log_repo': sync_log_repo,
            'project_repo': project_repo,
            'redis_service': redis_service,
            'sprint_repo': sprint_repo,
            'nats_service': container.nats_service,
            'nats_application_service': container.nats_application_service,
            'jira_user_api_service': jira_user_api_service,
            'jira_user_db_service': jira_user_db_service
        }

        return handlers, services_dict


@asynccontextmanager
async def lifespan_manager(app: FastAPI) -> AsyncGenerator[None, None]:
    """Context manager for FastAPI application lifespan"""
    log.info(f"Starting up {settings.APP_NAME}")

    # Initialize all dependencies
    await DependencyContainer.initialize()

    # Store important services in app state for access in endpoints
    container = DependencyContainer.get_instance()
    app.state.redis = container.redis_client
    app.state.nats = container.nats_service
    app.state.nats_event_service = container.nats_event_service

    # Start the NATS event service
    await container.nats_event_service.start()

    # Setup scheduled jobs
    setup_scheduled_jobs(container.scheduler)

    # Start the scheduler
    container.scheduler.start()
    app.state.scheduler = container.scheduler

    try:
        yield
    finally:
        log.info(f"Shutting down {settings.APP_NAME}")
        await DependencyContainer.cleanup()


def setup_scheduled_jobs(scheduler: AsyncIOScheduler) -> None:
    """Set up all scheduled jobs"""
    from apscheduler.triggers.interval import IntervalTrigger

    # Add token cleanup job
    async def cleanup_expired_tokens() -> None:
        try:
            db = await DependencyContainer.get_db_for_job()
            try:
                repository = SQLAlchemyRefreshTokenRepository(db)
                await repository.cleanup_expired_tokens()
                log.info("Completed expired tokens cleanup")
            finally:
                await db.close()
        except Exception as e:
            log.error(f"Error cleaning up expired tokens: {str(e)}")

    # Add token refresh check job
    async def check_tokens_for_refresh() -> None:
        try:
            db = await DependencyContainer.get_db_for_job()
            try:
                container = DependencyContainer.get_instance()
                user_repository = SQLAlchemyJiraUserRepository(db)
                refresh_token_repository = SQLAlchemyRefreshTokenRepository(db)
                token_refresh_service = TokenRefreshService(
                    container.redis_service,
                    user_repository,
                    refresh_token_repository
                )
                token_scheduler_service = TokenSchedulerService(
                    token_refresh_service,
                    refresh_token_repository
                )

                users = await user_repository.get_all_users()
                for user in users:
                    if user and user.user_id:
                        await token_scheduler_service.schedule_token_refresh(user.user_id)
                log.info("Completed token refresh check")
            finally:
                await db.close()
        except Exception as e:
            log.error(f"Error checking tokens for refresh: {str(e)}")

    # Schedule jobs
    scheduler.add_job(
        cleanup_expired_tokens,
        IntervalTrigger(hours=1),
        id='token_cleanup',
        replace_existing=True,
        misfire_grace_time=None
    )

    scheduler.add_job(
        check_tokens_for_refresh,
        IntervalTrigger(hours=24),
        id='token_refresh_check',
        replace_existing=True,
        misfire_grace_time=60
    )
