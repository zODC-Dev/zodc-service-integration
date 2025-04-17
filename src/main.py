
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.app.dependencies.container import lifespan_manager
from src.app.routers.jira_issue_router import router as jira_issue_router
from src.app.routers.jira_project_router import router as jira_project_router
from src.app.routers.jira_sprint_analytics_router import router as jira_sprint_analytics_router
from src.app.routers.jira_sprint_router import router as jira_sprint_router
from src.app.routers.jira_webhook_router import router as jira_webhook_router
from src.app.routers.media_router import router as media_router
from src.app.routers.microsoft_calendar_router import router as microsoft_calendar_router
from src.app.routers.system_config_router import router as system_config_router
from src.app.routers.util_router import router as util_router
from src.configs.settings import settings

# Define Prometheus instrumentator first
instrumentator = Instrumentator(
    should_respect_env_var=True,
    env_var_name="ENABLE_METRICS",
    should_instrument_requests_inprogress=True,
    excluded_handlers=[".*admin.*", "/metrics"],
    # env_var_name="ENABLE_METRICS",
    inprogress_name="fastapi_inprogress",
    inprogress_labels=True
)

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan_manager,
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
app.include_router(jira_sprint_analytics_router, prefix=settings.API_V1_STR +
                   "/jira/sprint-analytics", tags=["jira_sprint_analytics"])
app.include_router(jira_sprint_router, prefix=settings.API_V1_STR +
                   "/jira/sprint", tags=["jira_sprint"])
app.include_router(media_router, prefix=settings.API_V1_STR + "/media", tags=["media"])
app.include_router(system_config_router, prefix=settings.API_V1_STR + "/configs", tags=["system_config"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0",
                port=settings.PORT, reload=True)
