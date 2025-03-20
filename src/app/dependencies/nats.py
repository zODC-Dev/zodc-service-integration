from typing import Mapping

from fastapi import Depends

from src.app.dependencies.common import get_nats_service, get_redis_service
from src.app.dependencies.jira_issue import get_jira_issue_service
from src.app.dependencies.jira_user import get_jira_user_repository
from src.app.dependencies.refresh_token import get_refresh_token_repository
from src.app.services.jira_issue_service import JiraIssueService
from src.app.services.nats_event_service import NATSEventService
from src.app.services.nats_handlers.jira_issue_handler import JiraIssueMessageHandler, JiraIssueSyncRequestHandler
from src.app.services.nats_handlers.login_message_handler import JiraLoginHandler, MicrosoftLoginHandler
from src.app.services.nats_handlers.user_message_handler import UserMessageHandler
from src.domain.constants.nats_events import NATSSubscribeTopic
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.repositories.refresh_token_repository import IRefreshTokenRepository
from src.domain.services.nats_event_service import INATSEventService
from src.domain.services.nats_service import INATSRequestHandler, INATSService
from src.domain.services.redis_service import IRedisService


def get_nats_event_service(
    request_handlers: Mapping[str, INATSRequestHandler],
    nats_service: INATSService = Depends(get_nats_service),
    redis_service: IRedisService = Depends(get_redis_service),
    user_repository: IJiraUserRepository = Depends(get_jira_user_repository),
    refresh_token_repository: IRefreshTokenRepository = Depends(get_refresh_token_repository),
    jira_issue_service: JiraIssueService = Depends(get_jira_issue_service)
) -> INATSEventService:
    """Get NATS event service with all handlers configured"""
    # Configure message handlers
    message_handlers = {
        NATSSubscribeTopic.USER_EVENT.value:
            UserMessageHandler(redis_service),
        NATSSubscribeTopic.MICROSOFT_LOGIN.value:
            MicrosoftLoginHandler(redis_service, user_repository, refresh_token_repository),
        NATSSubscribeTopic.JIRA_LOGIN.value:
            JiraLoginHandler(redis_service, user_repository, refresh_token_repository),
        NATSSubscribeTopic.JIRA_ISSUE_UPDATE.value:
            JiraIssueMessageHandler(jira_issue_service)
    }

    # Configure request handlers
    request_handlers = {
        NATSSubscribeTopic.JIRA_ISSUE_SYNC.value:
            JiraIssueSyncRequestHandler(jira_issue_service)
    }

    # Create and return service
    return NATSEventService(
        nats_service=nats_service,
        message_handlers=message_handlers,
        request_handlers=request_handlers
    )
