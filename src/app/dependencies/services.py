from typing import List

from fastapi import Depends

from src.app.dependencies.container import DependencyContainer
from src.app.dependencies.repositories import (
    get_jira_issue_repository,
    get_jira_project_repository,
    get_jira_sprint_repository,
    get_jira_user_repository,
    get_media_repository,
    get_sync_log_repository,
    get_system_config_repository,
    get_workflow_mapping_repository,
)
from src.app.services.gantt_chart_service import GanttChartApplicationService
from src.app.services.jira_issue_history_service import JiraIssueHistoryApplicationService
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.app.services.jira_project_service import JiraProjectApplicationService
from src.app.services.jira_sprint_analytics_service import JiraSprintAnalyticsApplicationService
from src.app.services.jira_sprint_service import JiraSprintApplicationService
from src.app.services.jira_webhook_handlers.issue_create_webhook_handler import IssueCreateWebhookHandler
from src.app.services.jira_webhook_handlers.issue_delete_webhook_handler import IssueDeleteWebhookHandler
from src.app.services.jira_webhook_handlers.issue_update_webhook_handler import IssueUpdateWebhookHandler
from src.app.services.jira_webhook_handlers.jira_webhook_handler import JiraWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_close_webhook_handler import SprintCloseWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_create_webhook_handler import SprintCreateWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_delete_webhook_handler import SprintDeleteWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_start_webhook_handler import SprintStartWebhookHandler
from src.app.services.jira_webhook_handlers.sprint_update_webhook_handler import SprintUpdateWebhookHandler
from src.app.services.jira_webhook_handlers.user_create_webhook_handler import UserCreateWebhookHandler
from src.app.services.jira_webhook_handlers.user_delete_webhook_handler import UserDeleteWebhookHandler
from src.app.services.jira_webhook_handlers.user_update_webhook_handler import UserUpdateWebhookHandler
from src.app.services.jira_webhook_queue_service import JiraWebhookQueueService
from src.app.services.media_service import MediaApplicationService
from src.app.services.microsoft_calendar_service import MicrosoftCalendarApplicationService
from src.app.services.nats_application_service import NATSApplicationService
from src.app.services.nats_event_service import NATSEventService
from src.app.services.system_config_service import SystemConfigApplicationService
from src.app.services.util_service import UtilService
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.media_repository import IMediaRepository
from src.domain.repositories.system_config_repository import ISystemConfigRepository
from src.domain.repositories.workflow_mapping_repository import IWorkflowMappingRepository
from src.domain.services.gantt_chart_calculator_service import IGanttChartCalculatorService
from src.domain.services.jira_issue_database_service import IJiraIssueDatabaseService
from src.domain.services.jira_issue_history_database_service import IJiraIssueHistoryDatabaseService
from src.domain.services.jira_project_api_service import IJiraProjectAPIService
from src.domain.services.jira_sprint_analytics_service import IJiraSprintAnalyticsService
from src.domain.services.jira_sprint_api_service import IJiraSprintAPIService
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService
from src.domain.services.jira_user_api_service import IJiraUserAPIService
from src.domain.services.nats_service import INATSService
from src.domain.services.token_scheduler_service import ITokenSchedulerService
from src.domain.services.workflow_service_client import IWorkflowServiceClient
from src.infrastructure.services.azure_blob_storage_service import AzureBlobStorageService
from src.infrastructure.services.excel_file_service import ExcelFileService
from src.infrastructure.services.gantt_chart_calculator_service import GanttChartCalculatorService
from src.infrastructure.services.jira_issue_api_service import JiraIssueAPIService
from src.infrastructure.services.jira_issue_database_service import JiraIssueDatabaseService
from src.infrastructure.services.jira_issue_history_database_service import JiraIssueHistoryDatabaseService
from src.infrastructure.services.jira_project_api_service import JiraProjectAPIService
from src.infrastructure.services.jira_project_database_service import JiraProjectDatabaseService
from src.infrastructure.services.jira_service import JiraAPIClient
from src.infrastructure.services.jira_sprint_analytics_service import JiraSprintAnalyticsService
from src.infrastructure.services.jira_sprint_api_service import JiraSprintAPIService
from src.infrastructure.services.jira_sprint_database_service import JiraSprintDatabaseService
from src.infrastructure.services.jira_user_api_service import JiraUserAPIService
from src.infrastructure.services.jira_user_database_service import JiraUserDatabaseService
from src.infrastructure.services.jira_webhook_service import JiraWebhookService
from src.infrastructure.services.microsoft_calendar_service import MicrosoftCalendarService
from src.infrastructure.services.nats_service import NATSService
from src.infrastructure.services.nats_workflow_service_client import NATSWorkflowServiceClient
from src.infrastructure.services.redis_service import RedisService
from src.infrastructure.services.token_refresh_service import TokenRefreshService
from src.infrastructure.services.token_scheduler_service import TokenSchedulerService

# ============================ COMMON SERVICES =================================================


def get_redis_service() -> RedisService:
    """Get Redis service from container"""
    container = DependencyContainer.get_instance()
    return container.redis_service


def get_nats_service() -> NATSService:
    """Get NATS service from container"""
    container = DependencyContainer.get_instance()
    return container.nats_service


def get_nats_application_service() -> NATSApplicationService:
    """Get NATS application service from container"""
    container = DependencyContainer.get_instance()
    return container.nats_application_service


def get_jira_issue_api_service() -> JiraIssueAPIService:
    """Get Jira Issue API service from container"""
    container = DependencyContainer.get_instance()
    return container.jira_issue_api_service


def get_jira_project_api_service() -> JiraProjectAPIService:
    """Get Jira Project API service from container"""
    container = DependencyContainer.get_instance()
    return container.jira_project_api_service


def get_jira_issue_database_service() -> JiraIssueDatabaseService:
    """Get Jira Issue database service from container"""
    container = DependencyContainer.get_instance()
    return container.jira_issue_database_service


def get_jira_project_database_service() -> JiraProjectDatabaseService:
    """Get Jira Project database service from container"""
    container = DependencyContainer.get_instance()
    return container.jira_project_database_service


def get_jira_sprint_database_service() -> JiraSprintDatabaseService:
    """Get Jira Sprint database service from container"""
    container = DependencyContainer.get_instance()
    return container.jira_sprint_database_service


def get_jira_issue_history_database_service() -> JiraIssueHistoryDatabaseService:
    """Get Jira Issue History database service from container"""
    container = DependencyContainer.get_instance()
    return container.issue_history_db_service


def get_jira_user_database_service() -> JiraUserDatabaseService:
    """Get Jira User database service from container"""
    container = DependencyContainer.get_instance()
    return container.jira_user_db_service


def get_jira_issue_application_service() -> JiraIssueApplicationService:
    """Get Jira Issue application service from container"""
    container = DependencyContainer.get_instance()
    return container.jira_issue_application_service


def get_jira_project_application_service() -> JiraProjectApplicationService:
    """Get Jira Project application service from container"""
    container = DependencyContainer.get_instance()
    return container.jira_project_application_service


def get_jira_issue_history_application_service() -> JiraIssueHistoryApplicationService:
    """Get Jira Issue History application service from container"""
    container = DependencyContainer.get_instance()
    return container.issue_history_sync_service


def get_gantt_chart_application_service() -> GanttChartApplicationService:
    """Get Gantt Chart application service from container"""
    container = DependencyContainer.get_instance()
    return container.gantt_chart_service


def get_nats_event_service() -> NATSEventService:
    """Get NATS Event service from container"""
    container = DependencyContainer.get_instance()
    return container.nats_event_service


def get_token_refresh_service() -> TokenRefreshService:
    """Get Token Refresh service from container"""
    container = DependencyContainer.get_instance()
    return container.token_refresh_service


def get_token_scheduler_service() -> TokenSchedulerService:
    """Get Token Scheduler service from container"""
    container = DependencyContainer.get_instance()
    return container.token_scheduler_service


# ============================ TOKEN SCHEDULER SERVICE ===========================================


# async def get_token_refresh_service(
#     refresh_token_repository: IRefreshTokenRepository = Depends(get_refresh_token_repository),
#     redis_service: IRedisService = Depends(get_redis_service),
#     user_repository: IJiraUserRepository = Depends(get_jira_user_repository)
# ) -> ITokenRefreshService:
#     """Get the token refresh service."""
#     return TokenRefreshService(refresh_token_repository=refresh_token_repository, redis_service=redis_service, user_repository=user_repository)


# async def get_token_scheduler_service(
#     token_refresh_service: ITokenRefreshService = Depends(get_token_refresh_service),
#     refresh_token_repository: IRefreshTokenRepository = Depends(get_refresh_token_repository)
# ) -> TokenSchedulerService:
#     """Get the token scheduler service."""
#     return TokenSchedulerService(token_refresh_service=token_refresh_service, refresh_token_repository=refresh_token_repository)

# ============================ JIRA API CLIENT =================================================


async def get_jira_api_client(
    redis_service: RedisService = Depends(get_redis_service),
    token_scheduler_service: ITokenSchedulerService = Depends(get_token_scheduler_service),
):
    """Dependency for jira api client"""
    return JiraAPIClient(
        redis_service=redis_service,
        token_scheduler_service=token_scheduler_service,
    )


async def get_jira_api_admin_client(
    redis_service: RedisService = Depends(get_redis_service),
    token_scheduler_service: ITokenSchedulerService = Depends(get_token_scheduler_service),
):
    """Dependency for jira api client with admin auth"""
    return JiraAPIClient(
        redis_service=redis_service,
        token_scheduler_service=token_scheduler_service,
        use_admin_auth=True  # Sử dụng admin auth
    )

# ============================ JIRA SPRINTS =================================================


async def get_jira_sprint_api_service(
    jira_api_client=Depends(get_jira_api_client),
    jira_api_admin_client=Depends(get_jira_api_admin_client)
) -> IJiraSprintAPIService:
    """Get Jira sprint API service"""
    return JiraSprintAPIService(
        client=jira_api_client,
        admin_client=jira_api_admin_client
    )


# async def get_jira_sprint_database_service(
#     sprint_repository: IJiraSprintRepository = Depends(get_jira_sprint_repository)
# ) -> IJiraSprintDatabaseService:
#     """Get Jira sprint database service"""
#     return JiraSprintDatabaseService(sprint_repository)


async def get_jira_sprint_service(
    jira_sprint_api_service: IJiraSprintAPIService = Depends(get_jira_sprint_api_service),
    jira_sprint_database_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service),
    jira_issue_repository: IJiraIssueRepository = Depends(get_jira_issue_repository)
) -> JiraSprintApplicationService:
    """Get Jira sprint application service"""
    return JiraSprintApplicationService(
        jira_sprint_api_service=jira_sprint_api_service,
        jira_sprint_database_service=jira_sprint_database_service,
        jira_issue_repository=jira_issue_repository
    )

# ============================ JIRA USER SERVICE ===========================================


async def get_jira_user_api_service(
    jira_api_client=Depends(get_jira_api_client),
    jira_api_admin_client=Depends(get_jira_api_admin_client)
) -> IJiraUserAPIService:
    """Get Jira user API service"""
    return JiraUserAPIService(
        client=jira_api_client,
        admin_client=jira_api_admin_client
    )


# async def get_jira_user_database_service(
#     user_repository: IJiraUserRepository = Depends(get_jira_user_repository)
# ) -> IJiraUserDatabaseService:
#     """Get Jira user database service"""
#     return JiraUserDatabaseService(user_repository)

# ============================ JIRA ISSUE HISTORY DATABASE SERVICE ===========================================


# async def get_jira_issue_history_database_service(
#     jira_issue_history_repository: IJiraIssueHistoryRepository = Depends(get_jira_issue_history_repository)
# ) -> IJiraIssueHistoryDatabaseService:
#     """Get the Jira issue history database service"""
#     return JiraIssueHistoryDatabaseService(jira_issue_history_repository)


# async def get_jira_issue_api_service(
#     jira_api_client=Depends(get_jira_api_client),
#     jira_api_admin_client=Depends(get_jira_api_admin_client),
#     user_repository=Depends(get_jira_user_repository)
# ) -> JiraIssueAPIService:
#     """Get Jira issue API service"""
#     return JiraIssueAPIService(
#         client=jira_api_client,
#         user_repository=user_repository,
#         admin_client=jira_api_admin_client
#     )


# async def get_jira_issue_database_service(
#     issue_repository=Depends(get_jira_issue_repository)
# ) -> JiraIssueDatabaseService:
#     """Get Jira issue database service"""
#     return JiraIssueDatabaseService(issue_repository=issue_repository)


async def get_jira_issue_service(
    issue_api_service=Depends(get_jira_issue_api_service),
    issue_db_service=Depends(get_jira_issue_database_service),
    issue_repository=Depends(get_jira_issue_repository),
    project_repository=Depends(get_jira_project_repository),
    nats_service=Depends(get_nats_service),
    sync_log_repository=Depends(get_sync_log_repository),
) -> JiraIssueApplicationService:
    """Get Jira issue application service"""
    return JiraIssueApplicationService(
        jira_issue_db_service=issue_db_service,
        jira_issue_api_service=issue_api_service,
        issue_repository=issue_repository,
        project_repository=project_repository,
        nats_service=nats_service,
        sync_log_repository=sync_log_repository
    )

# ============================ JIRA ISSUE HISTORY SYNC SERVICE ===========================================


async def get_jira_issue_history_sync_service(
    jira_issue_api_service=Depends(get_jira_issue_api_service),
    jira_issue_history_database_service=Depends(get_jira_issue_history_database_service),
    jira_issue_database_service=Depends(get_jira_issue_database_service),
    jira_user_database_service=Depends(get_jira_user_database_service)
) -> JiraIssueHistoryApplicationService:
    """Get Jira issue history sync service"""
    return JiraIssueHistoryApplicationService(
        jira_issue_api_service=jira_issue_api_service,
        issue_history_db_service=jira_issue_history_database_service,
        jira_issue_db_service=jira_issue_database_service,
        jira_user_db_service=jira_user_database_service
    )

# ============================ JIRA PROJECT ===========================================


# def get_jira_project_api_service(
#     jira_api_client: JiraAPIClient = Depends(get_jira_api_client),
#     user_repository: IJiraUserRepository = Depends(get_jira_user_repository)
# ) -> IJiraProjectAPIService:
#     """Get Jira project API service instance."""
#     return JiraProjectAPIService(jira_api_client, user_repository)


# async def get_jira_project_database_service(
#     project_repository=Depends(get_jira_project_repository)
# ) -> IJiraProjectDatabaseService:
#     """Get Jira project database service instance."""
#     return JiraProjectDatabaseService(project_repository)


# def get_jira_project_application_service(
#     jira_project_api_service: IJiraProjectAPIService = Depends(get_jira_project_api_service),
#     jira_project_db_service: IJiraProjectDatabaseService = Depends(get_jira_project_database_service),
#     jira_issue_db_service: IJiraIssueDatabaseService = Depends(get_jira_issue_database_service),
#     jira_sprint_db_service: IJiraSprintDatabaseService = Depends(get_jira_sprint_database_service),
#     sync_session: IJiraSyncSession = Depends(get_sqlalchemy_jira_sync_session),
#     sync_log_repository: ISyncLogRepository = Depends(get_sync_log_repository),
#     jira_issue_api_service: IJiraIssueAPIService = Depends(get_jira_issue_api_service),
#     jira_issue_history_service: JiraIssueHistoryApplicationService = Depends(get_jira_issue_history_sync_service)
# ) -> JiraProjectApplicationService:
#     """Get Jira project application service instance."""
#     return JiraProjectApplicationService(
#         jira_project_api_service=jira_project_api_service,
#         jira_project_db_service=jira_project_db_service,
#         jira_issue_db_service=jira_issue_db_service,
#         jira_sprint_db_service=jira_sprint_db_service,
#         sync_session=sync_session,
#         sync_log_repository=sync_log_repository,
#         jira_issue_api_service=jira_issue_api_service,
#         jira_issue_history_service=jira_issue_history_service
#     )


# ============================ JIRA SPRINT ANALYTICS SERVICE ===========================================


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


# ============================ GANTT CHART SERVICE ===========================================


async def get_gantt_chart_calculator_service() -> IGanttChartCalculatorService:
    """Get the Gantt chart calculator service"""
    return GanttChartCalculatorService()


async def get_workflow_service_client(
    nats_client: INATSService = Depends(get_nats_service)
) -> IWorkflowServiceClient:
    """Get the workflow service client"""
    return NATSWorkflowServiceClient(nats_client)


async def get_gantt_chart_service(
    issue_repository: IJiraIssueRepository = Depends(get_jira_issue_repository),
    sprint_repository: IJiraSprintRepository = Depends(get_jira_sprint_repository),
    workflow_mapping_repository: IWorkflowMappingRepository = Depends(get_workflow_mapping_repository),
    gantt_calculator_service: IGanttChartCalculatorService = Depends(get_gantt_chart_calculator_service),
    workflow_service_client: IWorkflowServiceClient = Depends(get_workflow_service_client)
) -> GanttChartApplicationService:
    """Get the Gantt chart service"""
    return GanttChartApplicationService(issue_repository, sprint_repository, workflow_mapping_repository, gantt_calculator_service, workflow_service_client)


# ============================ JIRA WEBHOOK HANDLERS ===========================================


async def get_webhook_handlers(
    jira_issue_repository=Depends(get_jira_issue_repository),
    sync_log_repository=Depends(get_sync_log_repository),
    jira_issue_api_service=Depends(get_jira_issue_api_service),
    sprint_database_service=Depends(get_jira_sprint_database_service),
    jira_sprint_api_service=Depends(get_jira_sprint_api_service),
    jira_user_repository=Depends(get_jira_user_repository),
    jira_user_api_service=Depends(get_jira_user_api_service),
    user_database_service=Depends(get_jira_user_database_service),
    issue_history_sync_service=Depends(get_jira_issue_history_sync_service),
    jira_project_repository=Depends(get_jira_project_repository),
    redis_service=Depends(get_redis_service),
    nats_application_service=Depends(get_nats_application_service),
    jira_sprint_repository=Depends(get_jira_sprint_repository)
) -> List[JiraWebhookHandler]:
    """Get list of webhook handlers with dependencies"""
    return [
        # Issue handlers
        IssueCreateWebhookHandler(jira_issue_repository, sync_log_repository,
                                  jira_issue_api_service, jira_project_repository, redis_service),
        IssueUpdateWebhookHandler(jira_issue_repository=jira_issue_repository, sync_log_repository=sync_log_repository,
                                  jira_issue_api_service=jira_issue_api_service, issue_history_sync_service=issue_history_sync_service, nats_application_service=nats_application_service, jira_sprint_repository=jira_sprint_repository),
        IssueDeleteWebhookHandler(jira_issue_repository, sync_log_repository),

        # Sprint handlers
        SprintCreateWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service),
        SprintUpdateWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service),
        SprintStartWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service),
        SprintCloseWebhookHandler(sprint_database_service, sync_log_repository,
                                  jira_sprint_api_service, jira_issue_repository),
        SprintDeleteWebhookHandler(sprint_database_service, sync_log_repository, jira_sprint_api_service),

        # User handlers
        UserCreateWebhookHandler(user_database_service, sync_log_repository, jira_user_api_service),
        UserUpdateWebhookHandler(user_database_service, sync_log_repository, jira_user_api_service),
        UserDeleteWebhookHandler(user_database_service, sync_log_repository)
    ]


async def get_webhook_service(
    jira_issue_repository=Depends(get_jira_issue_repository),
    sync_log_repository=Depends(get_sync_log_repository),
    jira_issue_api_service=Depends(get_jira_issue_api_service),
    jira_sprint_api_service=Depends(get_jira_sprint_api_service),
    sprint_database_service=Depends(get_jira_sprint_database_service),
    issue_history_sync_service=Depends(get_jira_issue_history_sync_service),
    jira_project_repository=Depends(get_jira_project_repository),
    redis_service=Depends(get_redis_service),
    nats_application_service=Depends(get_nats_service),
    jira_sprint_repository=Depends(get_jira_sprint_repository)
) -> JiraWebhookService:
    """Get Jira webhook service"""
    return JiraWebhookService(
        jira_issue_repository,
        sync_log_repository,
        jira_issue_api_service,
        jira_sprint_api_service,
        sprint_database_service,
        issue_history_sync_service,
        jira_project_repository,
        redis_service,
        nats_application_service,
        jira_sprint_repository
    )


async def get_webhook_queue_service(
    jira_issue_api_service=Depends(get_jira_issue_api_service),
    jira_sprint_api_service=Depends(get_jira_sprint_api_service),
    jira_issue_history_service=Depends(get_jira_issue_history_database_service),
    webhook_handlers=Depends(get_webhook_handlers)
) -> JiraWebhookQueueService:
    """Get Jira webhook queue service"""
    return JiraWebhookQueueService(jira_issue_api_service, jira_sprint_api_service, jira_issue_history_service, webhook_handlers)

# =============================== MEDIA SERVICE ========================================================


async def get_media_service(
    media_repository: IMediaRepository = Depends(get_media_repository),
    blob_storage_service: AzureBlobStorageService = Depends(AzureBlobStorageService)
) -> MediaApplicationService:
    """Get the media service"""
    return MediaApplicationService(
        media_repository=media_repository,
        blob_storage_service=blob_storage_service
    )

# =============================== UTIL SERVICE ===================================================


def get_excel_file_service() -> ExcelFileService:
    """Get dependency for excel file service"""
    return ExcelFileService()


def get_blob_storage_service() -> AzureBlobStorageService:
    """Get dependency for blob storage service"""
    return AzureBlobStorageService()


async def get_util_service() -> UtilService:
    """Get dependency for util service"""
    excel_file_service = get_excel_file_service()
    blob_storage_service = get_blob_storage_service()
    return UtilService(excel_file_service=excel_file_service, blob_storage_service=blob_storage_service)


async def get_microsoft_calendar_service(
    redis_service: RedisService = Depends(get_redis_service)
) -> MicrosoftCalendarService:
    """Get Microsoft Calendar service."""
    return MicrosoftCalendarService(redis_service=redis_service)


async def get_microsoft_calendar_application_service(
    calendar_service: MicrosoftCalendarService = Depends(get_microsoft_calendar_service)
) -> MicrosoftCalendarApplicationService:
    """Get Microsoft Calendar application service."""
    return MicrosoftCalendarApplicationService(calendar_service=calendar_service)

# ============================ NATS =================================================


# async def get_nats_event_service(
#     request_handlers: Mapping[str, INATSRequestHandler],
#     nats_service: INATSService = Depends(get_nats_service),
#     redis_service: IRedisService = Depends(get_redis_service),
#     user_repository: IJiraUserRepository = Depends(get_jira_user_repository),
#     refresh_token_repository: IRefreshTokenRepository = Depends(get_refresh_token_repository),
#     jira_issue_application_service: JiraIssueApplicationService = Depends(get_jira_issue_service),
#     jira_sprint_repository: IJiraSprintRepository = Depends(get_jira_sprint_repository),
#     workflow_mapping_repository: IWorkflowMappingRepository = Depends(get_workflow_mapping_repository),
#     gantt_chart_service: GanttChartApplicationService = Depends(get_gantt_chart_service),
#     jira_issue_api_service: IJiraIssueAPIService = Depends(get_jira_issue_api_service)
# ) -> INATSEventService:
#     """Get NATS event service with all handlers configured"""
#     # Configure message handlers
#     message_handlers = {
#         NATSSubscribeTopic.USER_EVENT.value:
#             UserMessageHandler(redis_service),
#         NATSSubscribeTopic.MICROSOFT_LOGIN.value:
#             MicrosoftLoginMessageHandler(redis_service, user_repository, refresh_token_repository),
#         NATSSubscribeTopic.JIRA_LOGIN.value:
#             JiraLoginMessageHandler(user_repository, refresh_token_repository, redis_service),
#     }

#     # Configure request handlers
#     request_handlers = {
#         NATSSubscribeTopic.JIRA_ISSUE_SYNC.value:
#             JiraIssueSyncRequestHandler(jira_issue_application_service),
#         NATSSubscribeTopic.JIRA_ISSUE_LINK.value:
#             JiraIssueLinkRequestHandler(jira_issue_application_service),
#         NATSSubscribeTopic.WORKFLOW_SYNC.value:
#             WorkflowSyncRequestHandler(
#                 jira_issue_application_service,
#                 user_repository,
#                 jira_sprint_repository,
#                 workflow_mapping_repository,
#                 redis_service
#             ),
#         NATSSubscribeTopic.GANTT_CHART_CALCULATION.value:
#             GanttChartRequestHandler(gantt_chart_service),
#         NATSSubscribeTopic.NODE_STATUS_SYNC.value:
#             NodeStatusSyncHandler(jira_issue_api_service),
#         NATSSubscribeTopic.WORKFLOW_EDIT.value:
#             WorkflowEditRequestHandler(jira_issue_application_service, user_repository,
#                                        jira_sprint_repository, workflow_mapping_repository, redis_service)
#     }

#     # Create and return service
#     return NATSEventService(
#         nats_service=nats_service,
#         message_handlers=message_handlers,
#         request_handlers=request_handlers
#     )


def get_system_config_service(
    system_config_repository: ISystemConfigRepository = Depends(get_system_config_repository)
) -> SystemConfigApplicationService:
    """Get system config service"""
    return SystemConfigApplicationService(
        system_config_repository=system_config_repository
    )
