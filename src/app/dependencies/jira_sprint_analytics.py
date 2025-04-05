from fastapi import Depends

from src.app.controllers.jira_sprint_analytics_controller import JiraSprintAnalyticsController
from src.app.dependencies.gantt_chart import get_gantt_chart_service
from src.app.dependencies.jira_issue import get_jira_issue_database_service
from src.app.dependencies.jira_issue_history import get_jira_issue_history_database_service
from src.app.dependencies.jira_project import get_jira_project_api_service
from src.app.dependencies.jira_sprint import get_jira_sprint_database_service
from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.app.services.jira_sprint_analytics_service import JiraSprintAnalyticsApplicationService
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_sprint_analytics_service import IJiraSprintAnalyticsService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService
from src.infrastructure.services.jira_sprint_analytics_service import JiraSprintAnalyticsService


async def get_sprint_analytics_service(
    jira_project_api_service: IJiraProjectAPIService = Depends(get_jira_project_api_service),
    jira_issue_db_service: IJiraIssueDatabaseService = Depends(get_jira_issue_database_service),
    jira_sprint_db_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service),
    jira_issue_history_db_service: IJiraIssueHistoryDatabaseService = Depends(get_jira_issue_history_database_service)
) -> IJiraSprintAnalyticsService:
    """Get the sprint analytics service"""
    return JiraSprintAnalyticsService(
        jira_project_api_service,
        jira_issue_db_service,
        jira_sprint_db_service,
        jira_issue_history_db_service
    )


async def get_sprint_analytics_application_service(
    sprint_analytics_service: IJiraSprintAnalyticsService = Depends(get_sprint_analytics_service)
) -> JiraSprintAnalyticsApplicationService:
    """Get the sprint analytics application service"""
    return JiraSprintAnalyticsApplicationService(sprint_analytics_service)


async def get_sprint_analytics_controller(
    sprint_analytics_service: JiraSprintAnalyticsApplicationService = Depends(get_sprint_analytics_application_service),
    gantt_chart_service: GanttChartApplicationService = Depends(get_gantt_chart_service)
) -> JiraSprintAnalyticsController:
    """Get the sprint analytics controller"""
    return JiraSprintAnalyticsController(sprint_analytics_service, gantt_chart_service)
