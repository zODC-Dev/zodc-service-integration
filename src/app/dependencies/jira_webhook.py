from fastapi import Depends

from src.app.controllers.jira_webhook_controller import JiraWebhookController
from src.app.dependencies.jira_issue import get_jira_issue_application_service
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.infrastructure.services.jira_webhook_service import JiraWebhookService


def get_jira_webhook_service(
    jira_issue_application_service: JiraIssueApplicationService = Depends(get_jira_issue_application_service)
) -> JiraWebhookService:
    """Get the Jira webhook service"""
    return JiraWebhookService(jira_issue_application_service)


def get_webhook_controller(
    webhook_service: JiraWebhookService = Depends(get_jira_webhook_service)
) -> JiraWebhookController:
    """Get the Jira webhook controller"""
    return JiraWebhookController(webhook_service)
