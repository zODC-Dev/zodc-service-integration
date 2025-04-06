from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.configs.database import get_db
from src.domain.repositories.workflow_mapping_repository import IWorkflowMappingRepository
from src.infrastructure.repositories.sqlalchemy_workflow_mapping_repository import SQLAlchemyWorkflowMappingRepository


async def get_workflow_mapping_repository(
    session: AsyncSession = Depends(get_db)
) -> IWorkflowMappingRepository:
    """Get the workflow mapping repository"""
    return SQLAlchemyWorkflowMappingRepository(session)
