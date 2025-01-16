from fastapi import Depends

from src.app.dependencies.common import get_redis_service
from src.app.controllers.jira_controller import JiraController
from src.app.services.jira_service import JiraApplicationService
from src.infrastructure.services.jira_service import JiraService
from src.infrastructure.services.redis_service import RedisService


def get_jira_service(
    redis_service: RedisService = Depends(get_redis_service)
) -> JiraService:
    return JiraService(redis_service=redis_service)


def get_jira_application_service(
    jira_service: JiraService = Depends(get_jira_service)
) -> JiraApplicationService:
    return JiraApplicationService(jira_service=jira_service)


def get_jira_controller(
    jira_service: JiraApplicationService = Depends(get_jira_application_service)
) -> JiraController:
    return JiraController(jira_service=jira_service)
