from typing import Any, Dict

from fastapi import UploadFile

from src.domain.services.blob_storage_service import IBlobStorageService
from src.domain.services.excel_file_service import IExcelFileService


class UtilService:
    def __init__(
        self,
        excel_file_service: IExcelFileService,
        blob_storage_service: IBlobStorageService
    ) -> None:
        self.excel_file_service = excel_file_service
        self.blob_storage_service = blob_storage_service

    async def extract_excel(self, file: UploadFile) -> Dict[str, Any]:
        return await self.excel_file_service.extract_file(file)

    async def upload_excel_to_blob(self, file: UploadFile) -> str:
        # You might want to validate the file type here
        return await self.blob_storage_service.upload_file(
            file=file,
            container_name="excel-files"
        )
