from fastapi import Depends

from src.configs.database import get_db
from src.domain.repositories.project_repository import IProjectRepository
from src.infrastructure.repositories.sqlalchemy_project_repository import SQLAlchemyProjectRepository


def get_project_repository(session=Depends(get_db)) -> IProjectRepository:
    """Get a project repository instance."""
    return SQLAlchemyProjectRepository(session)
