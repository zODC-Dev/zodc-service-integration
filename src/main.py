from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis

from src.app.routers.jira_issue_router import router as jira_issue_router
from src.app.routers.jira_project_router import router as jira_project_router
from src.app.routers.jira_webhook_router import router as jira_webhook_router
from src.app.routers.microsoft_calendar_router import router as microsoft_calendar_router
from src.app.routers.util_router import router as util_router
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.app.services.jira_project_service import JiraProjectApplicationService
from src.app.services.nats_event_service import NATSEventService
from src.app.services.nats_handlers.jira_issue_handler import JiraIssueMessageHandler, JiraIssueSyncRequestHandler
from src.app.services.nats_handlers.jira_login_message_handler import JiraLoginMessageHandler
from src.app.services.nats_handlers.jira_project_sync_handler import JiraProjectSyncRequestHandler
from src.app.services.nats_handlers.microsoft_login_message_handler import MicrosoftLoginMessageHandler
from src.app.services.nats_handlers.user_message_handler import UserMessageHandler
from src.configs.database import get_db, init_db, session_maker
from src.configs.logger import log
from src.configs.settings import settings
from src.domain.constants.nats_events import NATSSubscribeTopic
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository
from src.infrastructure.repositories.sqlalchemy_jira_project_repository import SQLAlchemyJiraProjectRepository
from src.infrastructure.repositories.sqlalchemy_jira_sprint_repository import SQLAlchemyJiraSprintRepository
from src.infrastructure.repositories.sqlalchemy_jira_user_repository import SQLAlchemyJiraUserRepository
from src.infrastructure.repositories.sqlalchemy_refresh_token_repository import SQLAlchemyRefreshTokenRepository
from src.infrastructure.repositories.sqlalchemy_sync_log_repository import SQLAlchemySyncLogRepository
from src.infrastructure.services.jira_issue_database_service import JiraIssueDatabaseService
from src.infrastructure.services.jira_project_api_service import JiraProjectAPIService
from src.infrastructure.services.jira_project_database_service import JiraProjectDatabaseService
from src.infrastructure.services.jira_sprint_database_service import JiraSprintDatabaseService
from src.infrastructure.services.nats_service import NATSService
from src.infrastructure.services.redis_service import RedisService
from src.infrastructure.services.token_refresh_service import TokenRefreshService
from src.infrastructure.services.token_scheduler_service import TokenSchedulerService
from src.infrastructure.unit_of_works.sqlalchemy_jira_sync_session import SQLAlchemyJiraSyncSession

# Define Prometheus instrumentator first
instrumentator = Instrumentator(
    should_respect_env_var=True,
    env_var_name="ENABLE_METRICS",
    # Add these configurations
    should_instrument_requests_inprogress=True,
    excluded_handlers=[".*admin.*", "/metrics"],
    # env_var_name="ENABLE_METRICS",
    inprogress_name="fastapi_inprogress",
    inprogress_labels=True
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize configurations"""
    # Startup
    log.info(f"Starting up {settings.APP_NAME}")
    await init_db()

    # Initialize Redis
    redis_client = Redis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        encoding="utf-8",
        decode_responses=True
    )
    redis_service = RedisService(redis_client)
    app.state.redis = redis_client

    # Initialize NATS service
    nats_service = NATSService()
    await nats_service.connect()
    app.state.nats = nats_service

    # Initialize repositories with session factory
    db_generator = get_db()
    db = await anext(db_generator)

    user_repository = SQLAlchemyJiraUserRepository(db, redis_service)
    refresh_token_repository = SQLAlchemyRefreshTokenRepository(db)
    project_repository = SQLAlchemyJiraProjectRepository(db)
    sync_log_repository = SQLAlchemySyncLogRepository(db)

    # Initialize token services
    token_refresh_service = TokenRefreshService(redis_service, user_repository, refresh_token_repository)
    token_scheduler_service = TokenSchedulerService(token_refresh_service, refresh_token_repository)

    jira_issue_repository = SQLAlchemyJiraIssueRepository(db)
    # Initialize Jira services
    jira_issue_database_service = JiraIssueDatabaseService(
        jira_issue_repository
    )

    jira_issue_application_service = JiraIssueApplicationService(
        jira_issue_database_service, jira_issue_repository, nats_service, sync_log_repository)

    sync_session = SQLAlchemyJiraSyncSession(session_maker, redis_service)

    jira_project_api_service = JiraProjectAPIService(redis_service, token_scheduler_service, user_repository)
    jira_project_database_service = JiraProjectDatabaseService(project_repository)
    jira_sprint_repository = SQLAlchemyJiraSprintRepository(db)
    jira_sprint_database_service = JiraSprintDatabaseService(jira_sprint_repository)
    jira_project_application_service = JiraProjectApplicationService(
        jira_project_api_service,
        jira_project_database_service,
        jira_issue_database_service,
        jira_sprint_database_service,
        sync_session,
        sync_log_repository
    )

    # Initialize NATS Message Handlers with correct dependencies
    message_handlers = {
        NATSSubscribeTopic.USER_EVENT.value: UserMessageHandler(redis_service),
        NATSSubscribeTopic.MICROSOFT_LOGIN.value: MicrosoftLoginMessageHandler(
            redis_service=redis_service,
            user_repository=user_repository,
            refresh_token_repository=refresh_token_repository
        ),
        NATSSubscribeTopic.JIRA_LOGIN.value: JiraLoginMessageHandler(
            redis_service=redis_service,
            user_repository=user_repository,
            refresh_token_repository=refresh_token_repository
        ),
        NATSSubscribeTopic.JIRA_ISSUE_UPDATE.value: JiraIssueMessageHandler(jira_issue_application_service)
    }

    # Initialize NATS Request Handlers
    request_handlers = {
        NATSSubscribeTopic.JIRA_ISSUE_SYNC.value: JiraIssueSyncRequestHandler(jira_issue_application_service),
        NATSSubscribeTopic.JIRA_PROJECT_SYNC.value: JiraProjectSyncRequestHandler(
            jira_project_application_service, sync_log_repository)
    }

    # Initialize and start NATS Event Service
    nats_event_service = NATSEventService(
        nats_service=nats_service,
        message_handlers=message_handlers,
        request_handlers=request_handlers
    )
    await nats_event_service.start()
    app.state.nats_event_service = nats_event_service

    # Initialize and start APScheduler
    scheduler = AsyncIOScheduler()

    # Add token cleanup job
    async def cleanup_expired_tokens():
        try:
            # Get new db session
            db_generator = get_db()
            db = await anext(db_generator)
            try:
                repository = SQLAlchemyRefreshTokenRepository(db)
                await repository.cleanup_expired_tokens()
                log.info("Completed expired tokens cleanup")
            finally:
                await db.close()
        except Exception as e:
            log.error(f"Error cleaning up expired tokens: {str(e)}")

    # Add token refresh check job
    async def check_tokens_for_refresh():
        try:
            # Get new db session
            db_generator = get_db()
            db = await anext(db_generator)
            try:
                user_repository = SQLAlchemyJiraUserRepository(db, redis_service)
                refresh_token_repository = SQLAlchemyRefreshTokenRepository(db)
                token_refresh_service = TokenRefreshService(
                    redis_service,
                    user_repository,
                    refresh_token_repository
                )
                token_scheduler_service = TokenSchedulerService(
                    token_refresh_service,
                    refresh_token_repository
                )

                users = await user_repository.get_all_users()
                for user in users:
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

    # Start the scheduler
    scheduler.start()
    app.state.scheduler = scheduler

    try:
        yield
    finally:
        # Shutdown
        log.info(f"Shutting down {settings.APP_NAME}")

        # Shutdown scheduler
        if hasattr(app.state, "scheduler"):
            app.state.scheduler.shutdown()

        # Close connections
        if hasattr(app.state, "redis"):
            await app.state.redis.close()
        if hasattr(app.state, "nats"):
            await app.state.nats.disconnect()

        # Close database
        await db.close()


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    swagger_ui_init_oauth={
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": settings.CLIENT_AZURE_CLIENT_ID,
        "appName": settings.APP_NAME,
    },
)

# Add Prometheus instrumentation AFTER FastAPI app creation
instrumentator.instrument(app).expose(app, include_in_schema=True)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin)
                       for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(util_router, prefix=settings.API_V1_STR +
                   "/utils", tags=["utils"])
app.include_router(jira_project_router, prefix=settings.API_V1_STR + "/jira/projects", tags=["jira_projects"])
app.include_router(jira_issue_router, prefix=settings.API_V1_STR + "/jira/issues", tags=["jira_issues"])
app.include_router(microsoft_calendar_router, prefix=settings.API_V1_STR + "/microsoft", tags=["microsoft"])
app.include_router(jira_webhook_router, prefix=settings.API_V1_STR + "/jira-webhook", tags=["jira_webhook"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0",
                port=settings.PORT, reload=True)
