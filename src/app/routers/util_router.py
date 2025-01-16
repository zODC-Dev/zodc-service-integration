from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from src.app.controllers.util_controller import UtilController
from src.app.dependencies.permission import get_permission_service
from src.app.dependencies.util import get_util_controller
from src.app.middlewares.permission_middleware import require_permissions
from src.domain.services.permission_service import IPermissionService

router = APIRouter()


@router.post("/excel/extract")
async def extract_excel(
    file: Annotated[UploadFile, File(...)],
    controller: UtilController = Depends(get_util_controller)
):
    """Extract excel data in form create"""
    return await controller.extract_excel(file)


@router.post("/excel/upload")
async def upload_excel(
    file: Annotated[UploadFile, File(...)],
    controller: UtilController = Depends(get_util_controller)
):
    """Upload excel file to Azure Blob Storage"""
    return await controller.upload_excel_to_blob(file)


@router.get("/test")
@require_permissions(permissions=["system-role.create"], scope="system")
async def test(
    request: Request,
    controller: UtilController = Depends(get_util_controller),
    permission_service: IPermissionService = Depends(get_permission_service)
):
    """Download excel file from Azure Blob Storage"""
    return {"message": "Hello, World!"}
