from fastapi import Depends

from infrastructure.services.jira_issue_service import JiraIssueService
from src.app.controllers.jira_issue_controller import JiraIssueController
from src.app.dependencies.common import get_nats_service, get_redis_service
from src.app.dependencies.jira_user import get_jira_user_repository
from src.app.dependencies.refresh_token import get_token_scheduler_service
from src.app.services.jira_issue_service import JiraIssueApplicationService
from src.configs.database import get_db
from src.domain.repositories.jira_issue_repository import IJiraIssueRepository
from src.domain.repositories.jira_user_repository import IJiraUserRepository
from src.domain.services.jira_issue_service import IJiraIssueService
from src.domain.services.nats_service import INATSService
from src.domain.services.redis_service import IRedisService
from src.domain.services.token_scheduler_service import ITokenSchedulerService
from src.infrastructure.repositories.sqlalchemy_jira_issue_repository import SQLAlchemyJiraIssueRepository


def get_jira_issue_repository(
    session=Depends(get_db)
) -> IJiraIssueRepository:
    """Get the Jira issue repository."""
    return SQLAlchemyJiraIssueRepository(session=session)


def get_jira_issue_service(
    redis_service: IRedisService = Depends(get_redis_service),
    token_scheduler_service: ITokenSchedulerService = Depends(get_token_scheduler_service),
    user_repository: IJiraUserRepository = Depends(get_jira_user_repository)
) -> IJiraIssueService:
    """Get the Jira issue service."""
    return JiraIssueService(redis_service, token_scheduler_service, user_repository)


def get_jira_issue_application_service(
    jira_issue_service: IJiraIssueService = Depends(get_jira_issue_service),
    jira_issue_repository: IJiraIssueRepository = Depends(get_jira_issue_repository),
    nats_service: INATSService = Depends(get_nats_service)
) -> JiraIssueApplicationService:
    """Get the Jira issue service."""
    return JiraIssueApplicationService(
        jira_issue_service,
        jira_issue_repository,
        nats_service
    )


def get_jira_issue_controller(
    jira_issue_service: JiraIssueApplicationService = Depends(get_jira_issue_application_service)
) -> JiraIssueController:
    """Get the Jira issue controller."""
    return JiraIssueController(jira_issue_service)
