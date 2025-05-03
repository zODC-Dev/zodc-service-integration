from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from src.app.controllers.system_config_controller import SystemConfigController
from src.app.dependencies.controllers import get_system_config_controller
from src.app.schemas.requests.system_config import (
    SystemConfigCreateRequest,
    SystemConfigPatchRequest,
    SystemConfigUpdateRequest,
)
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.system_config import SystemConfigListResponse, SystemConfigResponse
from src.configs.database import get_db

router = APIRouter()


@router.get("", response_model=StandardResponse[SystemConfigListResponse])
async def list_configs(
    scope: Optional[str] = Query(None, description="Filter by scope (admin, general, or project)"),
    project_key: Optional[str] = Query(None, description="Filter by project key"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page", alias="pageSize"),
    search: Optional[str] = Query(None, description="Search by config key or description"),
    sort_by: Optional[str] = Query(
        None, description="Field to sort by (id, key, scope, type)", alias="sortBy"),
    sort_order: Optional[str] = Query(None, description="Sort order (asc or desc)", alias="sortOrder"),
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """List system configurations with optional filtering, searching, and sorting"""
    return await controller.list_configs(
        session=session,
        scope=scope,
        project_key=project_key,
        page=page,
        page_size=page_size,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order
    )


@router.get("/scopes", response_model=StandardResponse[List[str]])
async def list_scopes(
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """List all scopes"""
    return await controller.list_scopes(session=session)


@router.get("/{id}", response_model=StandardResponse[SystemConfigResponse])
async def get_config(
    id: int = Path(..., description="Configuration ID"),
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """Get a system configuration by ID"""
    return await controller.get_config(session=session, id=id)


@router.get("/keys/{key}", response_model=StandardResponse[SystemConfigResponse])
async def get_config_by_key(
    key: str = Path(..., description="Configuration key"),
    scope: str = Query("general", description="Configuration scope (general or admin or project)"),
    project_key: Optional[str] = Query(None, description="Project key (required if scope is 'project')"),
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """Get a system configuration by key, scope and optional project_key"""
    return await controller.get_config_by_key(
        session=session,
        key=key,
        scope=scope,
        project_key=project_key
    )


@router.get("/projects/{project_key}/keys/{key}", response_model=StandardResponse[SystemConfigResponse])
async def get_config_by_key_and_project_key(
    key: str = Path(..., description="Configuration key"),
    project_key: str = Path(..., description="Project key"),
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """Get a system configuration by key and project key"""
    return await controller.get_config_by_key_and_project_key(
        session=session,
        key=key,
        project_key=project_key
    )


@router.post("", response_model=StandardResponse[SystemConfigResponse])
async def create_config(
    data: SystemConfigCreateRequest,
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """Create a new system configuration"""
    return await controller.create_config(
        session=session,
        data=data
    )


@router.put("/{id}", response_model=StandardResponse[SystemConfigResponse])
async def update_config(
    data: SystemConfigUpdateRequest,
    id: int = Path(..., description="Configuration ID"),
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """Update an existing system configuration"""
    return await controller.update_config(
        session=session,
        id=id,
        data=data
    )


@router.patch("/{id}", response_model=StandardResponse[SystemConfigResponse])
async def patch_config(
    data: SystemConfigPatchRequest,
    id: int = Path(..., description="Configuration ID"),
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """Patch a system configuration with simpler value field.

    This endpoint allows updating:
    - type: Config type (int, float, string, bool, time)
    - value: The value for the config (must match the type)
    - scope: The scope (general, admin, project)
    - project_key: (required if scope is 'project')
    - description: Optional description
    """
    return await controller.patch_config(
        session=session,
        id=id,
        data=data
    )


@router.delete("/{id}", response_model=StandardResponse[bool])
async def delete_config(
    id: int = Path(..., description="Configuration ID"),
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """Delete a system configuration"""
    return await controller.delete_config(
        session=session,
        id=id
    )


@router.get("/projects/{project_key}", response_model=StandardResponse[SystemConfigListResponse])
async def get_project_configs(
    project_key: str = Path(..., description="Project key"),
    controller: SystemConfigController = Depends(get_system_config_controller),
    session: AsyncSession = Depends(get_db),
):
    """Get all configurations for a project, including global fallbacks"""
    return await controller.get_project_configs(
        session=session,
        project_key=project_key
    )
