from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from src.app.controllers.system_config_controller import SystemConfigController
from src.app.dependencies.controllers import get_system_config_controller
from src.app.schemas.requests.system_config import SystemConfigCreateRequest, SystemConfigUpdateRequest
from src.app.schemas.responses.base import StandardResponse
from src.app.schemas.responses.system_config import SystemConfigListResponse, SystemConfigResponse

router = APIRouter()


@router.get("", response_model=StandardResponse[SystemConfigListResponse])
async def list_configs(
    scope: Optional[str] = Query(None, description="Filter by scope (global or project)"),
    project_key: Optional[str] = Query(None, description="Filter by project key"),
    limit: int = Query(100, description="Limit the number of results"),
    offset: int = Query(0, description="Offset for pagination"),
    controller: SystemConfigController = Depends(get_system_config_controller),
):
    """List system configurations with optional filtering"""
    return await controller.list_configs(scope=scope, project_key=project_key, limit=limit, offset=offset)


@router.get("/{id}", response_model=StandardResponse[SystemConfigResponse])
async def get_config(
    id: int = Path(..., description="Configuration ID"),
    controller: SystemConfigController = Depends(get_system_config_controller),
):
    """Get a system configuration by ID"""
    return await controller.get_config(id=id)


@router.get("/keys/{key}", response_model=StandardResponse[SystemConfigResponse])
async def get_config_by_key(
    key: str = Path(..., description="Configuration key"),
    scope: str = Query("global", description="Configuration scope (global or project)"),
    project_key: Optional[str] = Query(None, description="Project key (required if scope is 'project')"),
    controller: SystemConfigController = Depends(get_system_config_controller),
):
    """Get a system configuration by key, scope and optional project_key"""
    return await controller.get_config_by_key(key=key, scope=scope, project_key=project_key)


@router.post("", response_model=StandardResponse[SystemConfigResponse])
async def create_config(
    data: SystemConfigCreateRequest,
    controller: SystemConfigController = Depends(get_system_config_controller),
):
    """Create a new system configuration"""
    return await controller.create_config(data=data)


@router.put("/{id}", response_model=StandardResponse[SystemConfigResponse])
async def update_config(
    data: SystemConfigUpdateRequest,
    id: int = Path(..., description="Configuration ID"),
    controller: SystemConfigController = Depends(get_system_config_controller),
):
    """Update an existing system configuration"""
    return await controller.update_config(id=id, data=data)


@router.delete("/{id}", response_model=StandardResponse[bool])
async def delete_config(
    id: int = Path(..., description="Configuration ID"),
    controller: SystemConfigController = Depends(get_system_config_controller),
):
    """Delete a system configuration"""
    return await controller.delete_config(id=id)


# Project-specific routes
router_projects = APIRouter(
    prefix="/api/v1/projects",
    tags=["system-config"],
)


@router_projects.get("/{project_key}/configs", response_model=StandardResponse[SystemConfigListResponse])
async def get_project_configs(
    project_key: str = Path(..., description="Project key"),
    controller: SystemConfigController = Depends(get_system_config_controller),
):
    """Get all configurations for a project, including global fallbacks"""
    return await controller.get_project_configs(project_key=project_key)
