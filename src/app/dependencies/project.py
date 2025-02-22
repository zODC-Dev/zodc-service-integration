from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.controllers.project_controller import ProjectController
from src.app.services.project_service import ProjectService
from src.configs.database import get_db
from src.infrastructure.repositories.sqlalchemy_project_repository import SQLAlchemyProjectRepository


async def get_project_repository(db: AsyncSession = Depends(get_db)):
    """Get the project repository."""
    return SQLAlchemyProjectRepository(db)


async def get_project_service(
    project_repository=Depends(get_project_repository)
):
    """Get the project service."""
    return ProjectService(project_repository)


async def get_project_controller(
    project_service=Depends(get_project_service)
):
    """Get the project controller."""
    return ProjectController(project_service)
