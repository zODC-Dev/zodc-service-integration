from fastapi import Depends

from src.app.controllers.jira_controller import JiraController
from src.app.services.jira_service import JiraApplicationService
from src.infrastructure.services.jira_service import JiraService


def get_jira_service() -> JiraService:
    return JiraService()


def get_jira_application_service(
    jira_service: JiraService = Depends(get_jira_service)
) -> JiraApplicationService:
    return JiraApplicationService(jira_service=jira_service)


def get_jira_controller(
    jira_service: JiraApplicationService = Depends(get_jira_application_service)
) -> JiraController:
    return JiraController(jira_service=jira_service)
