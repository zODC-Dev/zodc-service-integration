from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.database import get_db
from src.domain.repositories.jira_sprint_repository import IJiraSprintRepository
from src.domain.services.jira_sprint_database_service import IJiraSprintDatabaseService
from src.infrastructure.repositories.sqlalchemy_jira_sprint_repository import SQLAlchemyJiraSprintRepository
from src.infrastructure.services.jira_sprint_database_service import JiraSprintDatabaseService


async def get_jira_sprint_repository(
    session: AsyncSession = Depends(get_db)
) -> IJiraSprintRepository:
    """Get the Jira sprint repository"""
    return SQLAlchemyJiraSprintRepository(session)


async def get_jira_sprint_database_service(
    sprint_repository: IJiraSprintRepository = Depends(get_jira_sprint_repository)
) -> IJiraSprintDatabaseService:
    """Get the Jira sprint database service"""
    return JiraSprintDatabaseService(sprint_repository)
