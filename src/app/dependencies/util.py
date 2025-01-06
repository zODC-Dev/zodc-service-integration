from fastapi import Depends

from src.app.controllers.util_controller import UtilController
from src.app.services.util_service import UtilService
from src.infrastructure.services.azure_blob_storage_service import AzureBlobStorageService
from src.infrastructure.services.excel_file_service import ExcelFileService


def get_excel_file_service() -> ExcelFileService:
    """Get dependency for excel file service"""
    return ExcelFileService()


def get_blob_storage_service() -> AzureBlobStorageService:
    """Get dependency for blob storage service"""
    return AzureBlobStorageService()


async def get_util_service() -> UtilService:
    """Get dependency for util service"""
    excel_file_service = get_excel_file_service()
    blob_storage_service = get_blob_storage_service()
    return UtilService(excel_file_service=excel_file_service, blob_storage_service=blob_storage_service)


async def get_util_controller(util_service: UtilService = Depends(get_util_service)) -> UtilController:
    """Get dependency for util controller"""
    # Inject util service dependency to util controller
    return UtilController(util_service=util_service)
