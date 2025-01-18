from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from src.app.routers.jira_router import router as jira_router
from src.app.routers.util_router import router as util_router
from src.app.services.user_event_service import UserEventService
from src.configs.database import init_db
from src.configs.logger import log
from src.configs.settings import settings
from src.domain.entities.user_events import UserEventType
from src.infrastructure.messaging.user_event_handler import UserEventHandler
from src.infrastructure.services.nats_service import NATSService
from src.infrastructure.services.redis_service import RedisService


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

    # Start subscribers
    await start_nats_subscribers(nats_service, redis_service)

    yield

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


async def start_nats_subscribers(
    nats_service: NATSService,
    redis_service: RedisService
) -> None:
    """Start NATS subscribers"""
    # Create services
    user_event_service = UserEventService(redis_service)
    user_event_handler = UserEventHandler(user_event_service)

    # Subscribe to all user events
    for event_type in UserEventType:
        await nats_service.subscribe(
            subject=event_type.value,
            callback=user_event_handler.handle_message
        )

    log.info("NATS subscribers started")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0",
                port=settings.PORT, reload=True)
