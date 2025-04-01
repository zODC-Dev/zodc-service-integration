from src.app.controllers.jira_webhook_controller import JiraWebhookController
from src.infrastructure.services.jira_webhook_service import JiraWebhookService


def get_webhook_controller() -> JiraWebhookController:
    """Get the Jira webhook controller"""
    webhook_service = JiraWebhookService()
    return JiraWebhookController(webhook_service)
