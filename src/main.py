from contextlib import asynccontextmanager
from typing import AsyncGenerator

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
from src.infrastructure.repositories.sqlalchemy_refresh_token_repository import SQLAlchemyRefreshTokenRepository
from src.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from src.infrastructure.services.nats_service import NATSService
from src.infrastructure.services.redis_service import RedisService

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

    # Start subscribers
    nats_event_service = NATSEventService(nats_service, redis_service, user_repository, refresh_token_repository)
    await nats_event_service.start_nats_subscribers()

    yield

    # Cleanup
    try:
        await db.close()  # Close the database session
        await db_generator.aclose()  # Close the generator
    except Exception as e:
        log.error(f"Error closing database connection: {e}")

    # Shutdown
    log.info(f"Shutting down {settings.APP_NAME}")
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
