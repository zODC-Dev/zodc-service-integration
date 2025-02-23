from contextlib import asynccontextmanager
from typing import AsyncGenerator

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from redis.asyncio import Redis

from src.app.routers.jira_router import router as jira_router
from src.app.routers.microsoft_calendar_router import router as microsoft_calendar_router
from src.app.routers.util_router import router as util_router
from src.app.services.nats_event_service import NATSEventService
from src.configs.database import get_db, init_db
from src.configs.logger import log
from src.configs.settings import settings
from src.infrastructure.repositories.sqlalchemy_project_repository import SQLAlchemyProjectRepository
from src.infrastructure.repositories.sqlalchemy_refresh_token_repository import SQLAlchemyRefreshTokenRepository
from src.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from src.infrastructure.services.jira_service import JiraService
from src.infrastructure.services.nats_service import NATSService
from src.infrastructure.services.redis_service import RedisService
from src.infrastructure.services.token_refresh_service import TokenRefreshService
from src.infrastructure.services.token_scheduler_service import TokenSchedulerService

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

    # Initialize repositories
    db_generator = get_db()
    db = await anext(db_generator)  # Get the actual session from the generator

    user_repository = SQLAlchemyUserRepository(db, redis_service)
    refresh_token_repository = SQLAlchemyRefreshTokenRepository(db)
    project_repository = SQLAlchemyProjectRepository(db)

    # Initialize services
    token_refresh_service = TokenRefreshService(redis_service, user_repository, refresh_token_repository)
    token_scheduler_service = TokenSchedulerService(token_refresh_service, refresh_token_repository)

    # Initialize Jira service with token scheduler
    jira_service = JiraService(redis_service, token_scheduler_service)

    # Initialize and start APScheduler
    scheduler = AsyncIOScheduler()

    # Add token cleanup job
    async def cleanup_expired_tokens():
        try:
            # Get new db session using get_db
            db_generator = get_db()
            db = await anext(db_generator)

            repository = SQLAlchemyRefreshTokenRepository(db)
            await repository.cleanup_expired_tokens()
            log.info("Completed expired tokens cleanup")
        except Exception as e:
            log.error(f"Error cleaning up expired tokens: {str(e)}")

    scheduler.add_job(
        cleanup_expired_tokens,
        IntervalTrigger(hours=1),  # For testing
        id='token_cleanup',
        replace_existing=True,
        misfire_grace_time=None
    )

    # Add token refresh check job
    async def check_tokens_for_refresh():
        try:
            # Get new db session using get_db
            db_generator = get_db()
            db = await anext(db_generator)

            user_repository = SQLAlchemyUserRepository(db, redis_service)
            refresh_token_repository = SQLAlchemyRefreshTokenRepository(db)
            token_refresh_service = TokenRefreshService(redis_service, user_repository, refresh_token_repository)
            token_scheduler_service = TokenSchedulerService(token_refresh_service, refresh_token_repository)

            users = await user_repository.get_all_users()
            for user in users:
                await token_scheduler_service.schedule_token_refresh(user.user_id)
            log.info("Completed token refresh check")
        except Exception as e:
            log.error(f"Error checking tokens for refresh: {str(e)}")

    scheduler.add_job(
        check_tokens_for_refresh,
        IntervalTrigger(hours=24),  # For testing
        id='token_refresh_check',
        replace_existing=True,
        misfire_grace_time=60
    )

    # Start the scheduler
    scheduler.start()
    app.state.scheduler = scheduler

    # Start subscribers
    nats_event_service = NATSEventService(
        nats_service,
        redis_service,
        user_repository,
        refresh_token_repository,
        project_repository,
        jira_service
    )
    await nats_event_service.start_nats_subscribers()

    yield

    # Shutdown
    log.info(f"Shutting down {settings.APP_NAME}")

    # Shutdown scheduler
    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()

    # Close other connections
    if hasattr(app.state, "redis"):
        await app.state.redis.close()
    if hasattr(app.state, "nats"):
        await app.state.nats.disconnect()


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
app.include_router(jira_router, prefix=settings.API_V1_STR + "/jira", tags=["jira"])
app.include_router(microsoft_calendar_router, prefix=settings.API_V1_STR + "/microsoft", tags=["microsoft"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0",
                port=settings.PORT, reload=True)
