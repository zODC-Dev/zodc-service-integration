from typing import Mapping

from fastapi import Depends

from src.app.dependencies.common import (
    get_jira_sprint_repository,
    get_jira_user_repository,
    get_nats_service,
    get_redis_service,
    get_refresh_token_repository,
)
from src.app.dependencies.jira_issue import get_jira_issue_application_service
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.app.services.nats_event_service import NATSEventService
from src.app.services.nats_handlers.jira_issue_link_handler import JiraIssueLinkRequestHandler
from src.app.services.nats_handlers.jira_issue_sync_handler import JiraIssueSyncRequestHandler
from src.app.services.nats_handlers.jira_login_message_handler import JiraLoginMessageHandler
from src.app.services.nats_handlers.microsoft_login_message_handler import MicrosoftLoginMessageHandler
from src.app.services.nats_handlers.user_message_handler import UserMessageHandler
from src.app.services.nats_handlers.workflow_sync_handler import WorkflowSyncRequestHandler
from src.domain.constants.nats_events import NATSSubscribeTopic
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.services.nats_event_service import INATSEventService
from src.domain.services.nats_message_handler import INATSRequestHandler
from src.domain.services.nats_service import INATSService
from src.domain.services.redis_service import IRedisService


def get_nats_event_service(
    request_handlers: Mapping[str, INATSRequestHandler],
    nats_service: INATSService = Depends(get_nats_service),
    redis_service: IRedisService = Depends(get_redis_service),
    user_repository: IJiraUserRepository = Depends(get_jira_user_repository),
    refresh_token_repository: IRefreshTokenRepository = Depends(get_refresh_token_repository),
    jira_issue_application_service: JiraIssueApplicationService = Depends(get_jira_issue_application_service),
    jira_sprint_repository: IJiraSprintRepository = Depends(get_jira_sprint_repository),
) -> INATSEventService:
    """Get NATS event service with all handlers configured"""
    # Configure message handlers
    message_handlers = {
        NATSSubscribeTopic.USER_EVENT.value:
            UserMessageHandler(redis_service),
        NATSSubscribeTopic.MICROSOFT_LOGIN.value:
            MicrosoftLoginMessageHandler(redis_service, user_repository, refresh_token_repository),
        NATSSubscribeTopic.JIRA_LOGIN.value:
            JiraLoginMessageHandler(user_repository, refresh_token_repository, redis_service),
    }

    # Configure request handlers
    request_handlers = {
        NATSSubscribeTopic.JIRA_ISSUE_SYNC.value:
            JiraIssueSyncRequestHandler(jira_issue_application_service),
        NATSSubscribeTopic.JIRA_ISSUE_LINK.value:
            JiraIssueLinkRequestHandler(jira_issue_application_service),
        NATSSubscribeTopic.WORKFLOW_SYNC.value:
            WorkflowSyncRequestHandler(
                jira_issue_application_service,
                user_repository,
                jira_sprint_repository
            )
    }

    # Create and return service
    return NATSEventService(
        nats_service=nats_service,
        message_handlers=message_handlers,
        request_handlers=request_handlers
    )
