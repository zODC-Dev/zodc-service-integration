from fastapi import Depends

from src.app.services.system_config_service import SystemConfigApplicationService
from src.app.controllers.jira_issue_controller import JiraIssueController
from src.app.controllers.jira_project_controller import JiraProjectController
from src.app.controllers.jira_sprint_analytics_controller import JiraSprintAnalyticsController
from src.app.controllers.jira_sprint_controller import JiraSprintController
from src.app.controllers.jira_webhook_controller import JiraWebhookController
from src.app.controllers.media_controller import MediaController
from src.app.controllers.microsoft_calendar_controller import MicrosoftCalendarController
from src.app.controllers.system_config_controller import SystemConfigController
from src.app.controllers.util_controller import UtilController
from src.app.dependencies.repositories import get_jira_project_repository
from src.app.dependencies.services import (
    get_gantt_chart_service,
    get_jira_issue_history_sync_service,
    get_jira_issue_service,
    get_jira_project_application_service,
    get_jira_sprint_database_service,
    get_jira_sprint_service,
    get_media_service,
    get_microsoft_calendar_application_service,
    get_sprint_analytics_application_service,
    get_system_config_service,
    get_util_service,
    get_webhook_queue_service,
    get_webhook_service,
)
from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.app.services.jira_project_service import JiraProjectApplicationService
from src.app.services.jira_sprint_analytics_service import JiraSprintAnalyticsApplicationService
from src.app.services.media_service import MediaService
from src.app.services.microsoft_calendar_service import MicrosoftCalendarApplicationService
from src.app.services.util_service import UtilService
from src.domain.repositories.jira_project_repository import IJiraProjectRepository
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService


async def get_jira_issue_controller(
    issue_service=Depends(get_jira_issue_service),
    issue_history_service=Depends(get_jira_issue_history_sync_service),
) -> JiraIssueController:
    """Get Jira issue controller"""
    return JiraIssueController(
        jira_issue_service=issue_service,
        jira_issue_history_service=issue_history_service,
    )


def get_jira_project_controller(
    app_service: JiraProjectApplicationService = Depends(get_jira_project_application_service),
    project_repository: IJiraProjectRepository = Depends(get_jira_project_repository),
    jira_sprint_db_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service)
) -> JiraProjectController:
    """Get Jira project controller instance."""
    return JiraProjectController(app_service, project_repository, jira_sprint_db_service)


async def get_sprint_analytics_controller(
    sprint_analytics_service: JiraSprintAnalyticsApplicationService = Depends(get_sprint_analytics_application_service),
    gantt_chart_service: GanttChartApplicationService = Depends(get_gantt_chart_service)
) -> JiraSprintAnalyticsController:
    """Get the sprint analytics controller"""
    return JiraSprintAnalyticsController(sprint_analytics_service, gantt_chart_service)


async def get_webhook_controller(
    webhook_service=Depends(get_webhook_service),
    webhook_queue_service=Depends(get_webhook_queue_service)
) -> JiraWebhookController:
    """Get Jira webhook controller"""
    return JiraWebhookController(webhook_service, webhook_queue_service)


async def get_media_controller(
    media_service: MediaService = Depends(get_media_service)
) -> MediaController:
    """Get the media controller"""
    return MediaController(media_service=media_service)


async def get_util_controller(util_service: UtilService = Depends(get_util_service)) -> UtilController:
    """Get dependency for util controller"""
    # Inject util service dependency to util controller
    return UtilController(util_service=util_service)


def get_microsoft_calendar_controller(
    calendar_service: MicrosoftCalendarApplicationService = Depends(get_microsoft_calendar_application_service)
) -> MicrosoftCalendarController:
    """Get Microsoft Calendar controller."""
    return MicrosoftCalendarController(calendar_service=calendar_service)


async def get_jira_sprint_controller(
    sprint_service=Depends(get_jira_sprint_service)
) -> JiraSprintController:
    """Get Jira sprint controller"""
    return JiraSprintController(sprint_service=sprint_service)


def get_system_config_controller(
    system_config_service: SystemConfigApplicationService = Depends(get_system_config_service)
) -> SystemConfigController:
    """Get the SystemConfigController instance"""
    return SystemConfigController(
        system_config_service=system_config_service
    )
