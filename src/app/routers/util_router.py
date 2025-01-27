from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from src.app.controllers.util_controller import UtilController
from src.app.dependencies.util import get_util_controller

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
